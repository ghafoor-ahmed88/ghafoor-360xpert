array = [2,3,7,9]
function min(arr){
    let min = arr[0];
    for(let i=0; i<arr.length; i++){
        if(arr[i]<min){
            min = arr[i];
        }
    }
    return min;
}
console.log(min(array));