array= [5,3,4,6,6,5,]
function freq(arr, target){
    let count = 0;
    for(let i = 0; i < arr.length; i++){
        if(arr[i] == target){
            count++;
        }
    }
    return count;
}
console.log(freq(array , 6));