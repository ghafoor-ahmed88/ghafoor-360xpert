numbers = [2,3,4,6,4,3,2]
freq = {}
for i in numbers:
    if i not in freq:
        freq[i] = 1
    else:
        freq[i] += 1
print(freq)