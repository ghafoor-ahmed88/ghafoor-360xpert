number = [100,20,3,5]
target = 5

for num in number:
    if num == target:
        print("found at" , number.index(num))
        break
else:
    print("not found")