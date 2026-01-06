import random

test_length = 3
rndquestion = 0
previous_answers = []
for i in range (test_length):
    rndquestion = random.randint(1,10)
    for k in range (len(previous_answers)):
        if rndquestion == previous_answers[k]:
            rndquestion = random.randint(1,10)
    if rndquestion == 1:
        print("First Question")