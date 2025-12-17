array = [2,3,4,5]
function reverse(arr){
    var arr2 = []
    for (var i = arr.length-1; i >= 0; i--){
        arr2.push(arr[i])
    }
    return arr2
}

console.log(reverse(array))