"""
Name: Cierra Britt
Date: June 6, 2024

Problem: A string is simply an ordered collection of symbols selected from some alphabet and formed into a word; 
the length of a string is the number of symbols that it contains. An example of a length 21 DNA string 
(whose alphabet contains the symbols 'A', 'C', 'G', and 'T') is "ATGCTTCAGAAAGGTCTTACG."
Given: A DNA string s of length at most 1000 nt.
Return: Four integers (separated by spaces) counting the respective number of times that the symbols 'A', 'C', 'G', and 'T' occur in s.

Description: This script counts the occurrences of each nucleotide ('A', 'C', 'G', 'T') in a given DNA string.
"""

def count_nucleotides(dna_string):
    a_count = dna_string.count('A')
    c_count = dna_string.count('C')
    g_count = dna_string.count('G')
    t_count = dna_string.count('T')
    return a_count, c_count, g_count, t_count
if __name__ == "__main__":
    with open("rosalind_dna.txt", "r") as file:
        dna_string = file.read().strip()
    a, c, g, t = count_nucleotides(dna_string)
    print(a, c, g, t)