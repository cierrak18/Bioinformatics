# map_app.R
# Name: Cierra B.
# Air Pollution × Microbiome Explorer (genus/raw)
# Source: # Sources: https://rstudio.github.io/leaflet/articles/shiny.html , https://github.com/Nirzaree/ShinyWebAppWithFormAndLeafletMap

suppressPackageStartupMessages({
  library(shiny)          # app framework
  library(leaflet)        # interactive map
  library(leaflet.extras) # heatmap layer
  library(dplyr)          # data wrangling
  library(readr)          # fast CSV I/O
  library(DT)             # data table
  library(plotly)         # interactive scatter/lines
})

# ------------------------------ UI ------------------------------
ui <- fluidPage(
  titlePanel("Air Pollution × Microbiome Explorer"),

  sidebarLayout(
    sidebarPanel(width = 4,

      # Optional upload; if empty, app will try ./combined.csv
      fileInput("datafile", "Load combined CSV (optional)", accept = ".csv"),

      # Pollutant numeric field (your file uses concentration_ppm)
      selectInput("pollutant_metric", "Pollutant metric",
                  choices = c("concentration_ppm"), selected = "concentration_ppm"),

      # Numeric microbiome field used on map + correlation
      selectInput("micro_numeric", "Microbiome metric (numeric)",
                  choices = c("rel_pct_abund", "count", "total_count_run"),
                  selected = "rel_pct_abund"),

      # These are built after data loads
      uiOutput("genus_ui"),
      uiOutput("year_ui"),

      # Map display controls
      sliderInput("pt_size", "Point size", min = 3, max = 18, value = 8, step = 1),
      checkboxInput("heat_pollut", "Heatmap: pollutant", value = TRUE),
      checkboxInput("heat_micro",  "Heatmap: microbiome", value = TRUE),
      sliderInput("heat_radius", "Heat radius (px)", min = 10, max = 80, value = 35),

      selectInput("color_mode", "Color mode",
                  choices = c("Pollutant categories", "Pollutant value", "Microbiome value"),
                  selected = "Pollutant categories"),
      sliderInput("alpha", "Marker opacity", min = 0.2, max = 1, value = 0.8, step = 0.05),

      tags$hr(), h4("Correlation controls"),
      selectInput("corr_method", "Method",
                  choices = c("pearson", "spearman", "kendall"), selected = "pearson"),
      checkboxInput("log_x", "Log10 pollutant (x)", value = FALSE),
      checkboxInput("log_y", "Log10 microbiome (y)", value = FALSE)
    ),

    mainPanel(
      leafletOutput("map", height = 520),  # the map
      br(),
      h3("Correlation"),
      plotlyOutput("corr_plot", height = 420), # scatter + trend lines
      verbatimTextOutput("corr_stats"),        # r / p / N
      br(),
      h4("Per-year correlations (current filters)"),
      DTOutput("corr_year_table"),             # table by year
      br(),
      h3("Data"),
      DTOutput("table")                        # filtered raw table
    )
  )
)

# ---------------------------- SERVER ----------------------------
server <- function(input, output, session) {

  # ---------- DATA LOADING ----------
  # Read file input if present; otherwise fallback to ./combined.csv; else return NULL.
  dat_raw <- reactive({
    if (!is.null(input$datafile)) {
      read_csv(input$datafile$datapath, show_col_types = FALSE)
    } else if (file.exists("combined.csv")) {
      read_csv("combined.csv", show_col_types = FALSE)
    } else {
      NULL  # don't error; lets the basemap render
    }
  })

  # Normalize column names + type a few columns; error early if essentials missing.
  dat <- reactive({
    d <- dat_raw(); req(!is.null(d))

    # If dataset has 'Genus' (capital G), rename to lowercase 'genus' for consistency.
    if (!"genus" %in% names(d) && "Genus" %in% names(d)) {
      d <- d %>% rename(genus = Genus)
    }

    # Ensure required columns exist (per your combined.csv)
    need_cols <- c("city","year","genus","pollutant","concentration_ppm","lat","lon")
    if (!all(need_cols %in% names(d))) {
      stop("CSV is missing required columns: ",
           paste(setdiff(need_cols, names(d)), collapse = ", "))
    }

    # Coerce types and drop rows missing coordinates
    d %>%
      mutate(
        year              = as.integer(year),
        concentration_ppm = suppressWarnings(as.numeric(concentration_ppm)),
        rel_pct_abund     = suppressWarnings(as.numeric(rel_pct_abund)),
        count             = suppressWarnings(as.numeric(count)),
        total_count_run   = suppressWarnings(as.numeric(total_count_run)),
        lat               = as.numeric(lat),
        lon               = as.numeric(lon)
      ) %>%
      filter(!is.na(lat), !is.na(lon))
  })

  # ---------- DYNAMIC UI ----------
  # Genus selector with "All genera"
  output$genus_ui <- renderUI({
    d <- dat_raw()
    if (is.null(d) || (!"genus" %in% names(d) && !"Genus" %in% names(d)))
      return(helpText("Load data to filter by genus."))

    # Build choices from whichever capitalization exists
    gvals <- if ("genus" %in% names(d)) d$genus else d$Genus
    choices <- c("All genera", sort(unique(gvals)))
    selectizeInput("genus", "Genus (filter)",
                   choices = choices, selected = "All genera", multiple = FALSE)
  })

  # Year range slider from data
  output$year_ui <- renderUI({
    d <- dat_raw()
    if (is.null(d) || !"year" %in% names(d))
      return(helpText("Load data to enable year range."))
    yr <- suppressWarnings(as.integer(d$year))
    sliderInput("year_rng", "Year range",
                min = min(yr, na.rm = TRUE),
                max = max(yr, na.rm = TRUE),
                value = c(min(yr, na.rm = TRUE), max(yr, na.rm = TRUE)),
                step = 1, sep = "")
  })

  # ---------- BASEMAP (always) ----------
  output$map <- renderLeaflet({
    leaflet() |>
      addTiles() |>                                # simple OSM fallback
      addProviderTiles(providers$CartoDB.Positron, # clean basemap
                       group = "Positron") |>
      addScaleBar(position = "bottomleft") |>
      addLayersControl(
        baseGroups = c("Positron"),
        overlayGroups = c("Points", "Heat: pollutant", "Heat: microbiome"),
        options = layersControlOptions(collapsed = TRUE)
      )
  })

  # ---------- FILTERED VIEW ----------
  # Apply filters for year and genus. When "All genera", skip genus filter.
  d_filtered <- reactive({
    d <- dat(); req(nrow(d) > 0)

    # Year filter
    if (!is.null(input$year_rng))
      d <- d %>% filter(year >= input$year_rng[1], year <= input$year_rng[2])

    # Genus filter (skip if "All genera")
    if (!is.null(input$genus) && input$genus != "All genera")
      d <- d %>% filter(genus == input$genus)

    d
  })

  # ---------- MAP LAYERS ----------
  # Update points/heatmaps/fit whenever data or controls change.
  observe({
    d <- d_filtered(); req(nrow(d) > 0)

    # Palettes for coloring
    pal_val <- colorNumeric("viridis", domain = NULL)   # for numeric values
    pal_cat <- colorFactor("Set1", d$pollutant)         # for pollutant categories

    # Microbiome numeric field to color/heat
    micro_col  <- req(input$micro_numeric); req(micro_col %in% names(d))
    micro_vals <- d[[micro_col]]

    # Choose the point color rule
    col_vals <- switch(input$color_mode,
      "Pollutant categories" = pal_cat(d$pollutant),
      "Pollutant value"      = pal_val(d$concentration_ppm),
      "Microbiome value"     = pal_val(micro_vals)
    )

    # Clear previous layers and redraw
    leafletProxy("map") %>%
      clearGroup("Points") %>%
      clearGroup("Heat: pollutant") %>%
      clearGroup("Heat: microbiome") %>%
      addCircleMarkers(
        lng = d$lon, lat = d$lat,
        radius = input$pt_size,
        fillColor = col_vals, fillOpacity = input$alpha,
        color = "#444444", weight = 0.6, opacity = 0.7,
        group = "Points",
        label = sprintf(
          "%s<br/>%s %g<br/>Genus: %s<br/>%s: %s",
          d$city, d$pollutant, d$concentration_ppm, d$genus,
          input$micro_numeric, signif(micro_vals, 5)
        ) %>% lapply(htmltools::HTML)
      )

    # Optional pollutant heatmap (intensity = concentration)
    if (isTRUE(input$heat_pollut)) {
      leafletProxy("map") %>% addHeatmap(
        lng = d$lon, lat = d$lat,
        intensity = d$concentration_ppm,
        radius = input$heat_radius, blur = input$heat_radius,
        max = max(d$concentration_ppm, na.rm = TRUE),
        group = "Heat: pollutant"
      )
    }

    # Optional microbiome heatmap (intensity = selected micro numeric)
    if (isTRUE(input$heat_micro)) {
      leafletProxy("map") %>% addHeatmap(
        lng = d$lon, lat = d$lat,
        intensity = micro_vals,
        radius = input$heat_radius, blur = input$heat_radius,
        max = max(micro_vals, na.rm = TRUE),
        group = "Heat: microbiome"
      )
    }

    # Fit the map view to the visible points
    rng  <- range(d$lon, na.rm = TRUE)
    latr <- range(d$lat, na.rm = TRUE)
    leafletProxy("map") %>% fitBounds(rng[1], latr[1], rng[2], latr[2])
  })

  # ---------- CORRELATION DATA PREP ----------
  # Builds numeric x (pollutant) and y (selected microbiome metric),
  # carries 'genus' + 'year', applies optional log10, and flags "All genera" mode.
  corr_prep <- reactive({
    d <- d_filtered(); req(nrow(d) > 1)

    yname <- req(input$micro_numeric); req(yname %in% names(d))

    dd <- d %>%
      transmute(
        year,
        genus = as.character(genus),                                  # ensure always present/character
        x = suppressWarnings(as.numeric(concentration_ppm)),          # pollutant
        y = suppressWarnings(as.numeric(.data[[yname]]))              # microbiome
      ) %>%
      filter(is.finite(x), is.finite(y))                              # drop NAs/non-finite

    req(nrow(dd) > 1)

    # Optional log10 transforms (drop non-positives first)
    if (isTRUE(input$log_x)) dd <- dd %>% filter(x > 0) %>% mutate(x = log10(x))
    if (isTRUE(input$log_y)) dd <- dd %>% filter(y > 0) %>% mutate(y = log10(y))

    dd <- dd %>% filter(is.finite(x), is.finite(y))                   # clean again post-log
    req(nrow(dd) > 1)

    dd$all_genera <- identical(input$genus, "All genera")             # TRUE when viewing all genera
    dd
  })

  # ---------- CORRELATION STATS ----------
  # Shows N, r, p for the current filters and log settings.
  output$corr_stats <- renderText({
    dd <- corr_prep()
    m  <- match.arg(input$corr_method, c("pearson","spearman","kendall"))
    ct <- suppressWarnings(cor.test(dd$x, dd$y, method = m, exact = FALSE))
    paste0(
      "Method: ", m, "\n",
      "N = ", length(dd$x), "\n",
      "r = ", signif(unname(ct$estimate), 4), "\n",
      "p = ", signif(ct$p.value, 4)
    )
  })

  # ---------- CORRELATION PLOT ----------
  # - If "All genera": color markers by genus and draw per-genus regression lines.
  # - Always plot an overall trend line across the visible points.
  output$corr_plot <- renderPlotly({
    dd <- corr_prep()

    # Axis labels reflect log toggles
    xlab <- paste0(ifelse(input$log_x,"log10(",""), "concentration_ppm", ifelse(input$log_x,")",""))
    ylab <- paste0(ifelse(input$log_y,"log10(",""), input$micro_numeric, ifelse(input$log_y,")",""))

    p <- plot_ly()  # start empty and add layers

    if (isTRUE(dd$all_genera[1])) {
      # ---- All genera mode: colored markers by genus ----
      p <- add_markers(
        p, data = dd, x = ~x, y = ~y, color = ~genus, colors = "Set1",
        text = ~paste0("Genus: ", genus, "<br>x: ", signif(x,4), "<br>y: ", signif(y,4)),
        hovertemplate = "%{text}<extra></extra>"
      )

      # ---- Per-genus regression lines (match colors using split=~genus) ----
      line_df <- dd %>%
        dplyr::group_by(genus) %>%
        dplyr::group_modify(function(dat, key) {
          # Skip groups with constant x or <2 rows
          if (nrow(dat) < 2 || diff(range(dat$x)) == 0) {
            return(tibble(genus = key$genus[1], x = numeric(0), y = numeric(0)))
          }
          fit <- tryCatch(lm(y ~ x, data = dat), error = function(e) NULL)
          if (is.null(fit)) {
            return(tibble(genus = key$genus[1], x = numeric(0), y = numeric(0)))
          }
          xs <- seq(min(dat$x), max(dat$x), length.out = 100)
          tibble(genus = key$genus[1], x = xs, y = predict(fit, newdata = data.frame(x = xs)))
        }) %>%
        dplyr::ungroup()

      if (nrow(line_df) > 0) {
        p <- add_lines(
          p, data = line_df, x = ~x, y = ~y, split = ~genus,
          hoverinfo = "none", showlegend = FALSE
        )
      }

    } else {
      # ---- Single-genus mode: one color, no legend ----
      p <- add_markers(
        p, data = dd, x = ~x, y = ~y,
        text = ~paste0("x: ", signif(x,4), "<br>y: ", signif(y,4)),
        hovertemplate = "%{text}<extra></extra>",
        showlegend = FALSE
      )
    }

    # ---- Overall trend line across all visible points ----
    fit_all <- tryCatch(lm(y ~ x, data = dd), error = function(e) NULL)
    if (!is.null(fit_all)) {
      xs <- seq(min(dd$x), max(dd$x), length.out = 120)
      overall <- data.frame(x = xs, y = predict(fit_all, newdata = data.frame(x = xs)))
      p <- add_lines(p, data = overall, x = ~x, y = ~y,
                     name = "overall trend", hoverinfo = "none",
                     line = list(width = 1.5))
    }

    # Final layout for the correlation figure
    p %>% layout(
      xaxis = list(title = xlab),
      yaxis = list(title = ylab),
      legend = list(orientation = "h", y = -0.15),
      margin = list(l = 60, r = 20, b = 55, t = 10)
    )
  })

  # ---------- PER-YEAR CORRELATIONS ----------
  # Correlation N and r by year for current filters/log choices.
  output$corr_year_table <- renderDT({
    dd <- corr_prep()
    m  <- match.arg(input$corr_method, c("pearson","spearman","kendall"))
    out <- dd %>%
      group_by(year) %>%
      summarize(
        N = n(),
        r = suppressWarnings(if (N > 1) cor(x, y, method = m, use = "complete.obs") else NA_real_),
        .groups = "drop"
      ) %>%
      mutate(r = round(r, 4)) %>%
      arrange(desc(N))
    datatable(out, options = list(pageLength = 8, dom = "tip"), rownames = FALSE)
  })

  # ---------- FILTERED RAW TABLE ----------
  output$table <- renderDT({
    d <- d_filtered(); req(nrow(d) > 0)
    datatable(d, options = list(pageLength = 10, scrollX = TRUE))
  })
}

# Boot the app
shinyApp(ui, server)
