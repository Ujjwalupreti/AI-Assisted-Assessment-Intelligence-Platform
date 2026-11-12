import hashlib
import json

target = '9d574e1d3c5ed212edee33e2478e5a62cdecc5b5cb365479c4eb99e9d342aa38'

def try_hash(s):
    if hashlib.sha256(s.encode('utf-8')).hexdigest() == target:
        print(f"FOUND MATCH: '{s}'")
        return True
    return False

# Try many combinations
for opt in ['A', 'B', 'C', 'D', 'a', 'b', 'c', 'd', '1', '2', '3', '4', '0']:
    if try_hash(opt): break
    if try_hash(f" {opt}"): break
    if try_hash(f"{opt} "): break
    if try_hash(f"Option {opt}"): break
    if try_hash(f"option_{opt}"): break
    if try_hash(f"Option_{opt}"): break
    
# Try the full text of options
options = [
    "A FIFO data structure", 
    "A LIFO data structure", 
    "A sorting algorithm", 
    "A database table",
    "Stack",
    "Structured Query Language"
]
for o in options:
    if try_hash(o): break
    if try_hash(o.lower()): break
    if try_hash(o.upper()): break

print("Done brute forcing.")
