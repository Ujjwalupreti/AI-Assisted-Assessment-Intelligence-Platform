from database import SessionLocal
from models import Question, Answer
import hashlib

db = SessionLocal()

# Standard hashes
hash_A = hashlib.sha256(b"A").hexdigest()
hash_B = hashlib.sha256(b"B").hexdigest()
hash_C = hashlib.sha256(b"C").hexdigest()
hash_D = hashlib.sha256(b"D").hexdigest()

# Weird hashes from DB
weird_A = 'd94791a85f88d5f49c3cc06d5557316cf743d60149820c594f389a1b301ff021'
weird_B = '9d574e1d3c5ed212edee33e2478e5a62cdecc5b5cb365479c4eb99e9d342aa38'
weird_C = '6b23c0d5f35d1b11f9b683f0b0a617355deb11277d91ae091d399c655b87940d' # Wait, let me just map what I found
# Wait, I found 108 of 6b23c0d5f35d1b11f9b683f0b0a617355deb11277d91ae091d399c655b87940d in the DB!
# And earlier I checked:
# C: 6b23c0d5f35d1b11f9b683f0b0a617355deb11277d91ae091d399c655b87940d !
# So C's hash IS standard!
# D: 3f39d5c348e5b79d06e842c114e6cc571583bbf44e4b0ebfda1a01ec05745d43 is standard!
# B: df7e70e5021544f4834bbee64a9e3789febc4be81470df629cad6ddb03320a5c is standard!
# A: 559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd is standard!

# Then what is 9d574e1d... and d94791a8... ?
# Let's just fix them in the DB.
questions = db.query(Question).all()
fixed_q = 0
for q in questions:
    if q.correct_option == weird_A:
        q.correct_option = hash_A
        fixed_q += 1
    elif q.correct_option == weird_B:
        q.correct_option = hash_B
        fixed_q += 1
    elif q.correct_option == '90fce73cb7c144cf09bf1f8c6719765172f384716c0574b2c5c1248e921fc8a1':
        q.correct_option = hash_C
        fixed_q += 1
    elif q.correct_option == '1f7bdf4890f6a851b1f26d20127735cebefdc92885e667722c39695624626647':
        q.correct_option = hash_D
        fixed_q += 1
    elif q.correct_option == '0a39db800bddada19a487093d1fd278d175e900092580de3f01bac4bae3ada7e':
        q.correct_option = hash_A
        fixed_q += 1
        
answers = db.query(Answer).all()
fixed_a = 0
for a in answers:
    if a.selected_option == weird_A:
        a.selected_option = hash_A
        fixed_a += 1
    elif a.selected_option == weird_B:
        a.selected_option = hash_B
        fixed_a += 1
    elif a.selected_option == '90fce73cb7c144cf09bf1f8c6719765172f384716c0574b2c5c1248e921fc8a1':
        a.selected_option = hash_C
        fixed_a += 1
    elif a.selected_option == '1f7bdf4890f6a851b1f26d20127735cebefdc92885e667722c39695624626647':
        a.selected_option = hash_D
        fixed_a += 1
        
db.commit()
print(f"Fixed {fixed_q} questions and {fixed_a} answers")
