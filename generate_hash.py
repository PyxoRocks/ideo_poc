#!/usr/bin/env python3
"""
Script utilitaire pour générer des hashes SHA-256 pour les codes d'accès.
Utilisez ce script pour créer un nouveau hash si vous voulez changer le code d'accès.
"""

import hashlib
import sys

def generate_hash(password):
    """Génère un hash SHA-256 pour un mot de passe donné"""
    return hashlib.sha256(password.encode()).hexdigest()

def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_hash.py <votre_code_d_acces>")
        print("Exemple: python generate_hash.py mon_nouveau_code")
        sys.exit(1)
    
    password = sys.argv[1]
    hash_value = generate_hash(password)
    
    print(f"Code d'accès: {password}")
    print(f"Hash SHA-256: {hash_value}")
    print("\nCopiez cette ligne dans votre fichier .streamlit/secrets.toml :")
    print(f'ACCESS_CODE_HASH = "{hash_value}"')

if __name__ == "__main__":
    main() 