numbers = [10, 5, 30, 25]
sum = 0


for num in range(len(numbers)):
    sum += numbers[num]
    
print("sum is:", sum)

average = sum/ len(numbers)

print("avg is:", average)