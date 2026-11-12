import hashlib

target1 = '9d574e1d3c5ed212edee33e2478e5a62cdecc5b5cb365479c4eb99e9d342aa38'
target2 = 'd94791a85f88d5f49c3cc06d5557316cf743d60149820c594f389a1b301ff021'

def check_target(target):
    for i in range(256):
        try:
            s = chr(i)
            if hashlib.sha256(s.encode()).hexdigest() == target:
                print(f"Target {target} is '{s}'")
                return
        except: pass
    
    # Check lowercase strings, uppercase, etc
    for s in ['option_a', 'option_b', 'option_c', 'option_d', 'A', 'B', 'C', 'D', 'a', 'b', 'c', 'd']:
        if hashlib.sha256(s.encode()).hexdigest() == target:
            print(f"Target {target} is '{s}'")
            return
            
    # Try finding in the first 10k integers as strings
    for i in range(10000):
        if hashlib.sha256(str(i).encode()).hexdigest() == target:
            print(f"Target {target} is '{i}'")
            return
            
    print(f"Target {target} not found")

check_target(target1)
check_target(target2)
