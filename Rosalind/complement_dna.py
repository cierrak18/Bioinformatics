"""Name: Cierra Britt
    Date: December 2, 2025
    Problem: In DNA strings, symbols 'A' and 'T' are complements of each other, as are 'C' and 'G'.The reverse complement of a 
    DNA string s is the string sc formed by reversing the symbols of s, then taking the complement of each symbol (e.g., 
    the reverse complement of "GTCA" is "TGAC"). 
    Given: A DNA string s of length at most 1000 bp. 
    Return: The reverse complement sc of s.
    
    Description: The reverse complement sc of s.This script reads a DNA string from a file, computes its reverse complement,
                 and prints the result.
    """
def complement_dna(dna_string):
    """Returns the complementary DNA string by replacing each nucleotide with its complement:
    'A' with 'T', 'T' with 'A', 'C' with 'G', and 'G' with 'C'."""
    complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
    return ''.join(complement[nucleotide] for nucleotide in dna_string)
if __name__ == "__main__":
    with open("rosalind_revc.txt", "r") as file:
        dna_string = file.read().strip()
    read_string = complement_dna(dna_string)
    reverse_string = read_string[::-1]
    print(reverse_string)