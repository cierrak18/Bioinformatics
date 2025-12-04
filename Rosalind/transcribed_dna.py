""" 
Name: Cierra Britt
Date: December 2, 2025

Problem: An RNA string is a string formed from the alphabet containing 'A', 'C', 'G', and 'U'.
Given a DNA string t corresponding to a coding strand, its transcribed RNA string u is formed by replacing 
all occurrences of 'T' in t with 'U' in u.
Given: A DNA string t having length at most 1000 nt.
Return: The transcribed RNA string of t.

Description: Transcription is the process of copying a segment of DNA into RNA. The RNA is similar to DNA except that it contains the
nucleotide uracil (U) in place of thymine (T)."""
def transcribed_dna(rna_string):
    """Transcribes a DNA string into RNA by replacing all occurrences of 'T' with 'U'."""
    return dna_string.replace('T', 'U')
if __name__ == "__main__":
    with open("rosalind_rna.txt", "r") as file:
        dna_string = file.read().strip()
    rna_string = transcribed_dna(dna_string)
    print(rna_string)