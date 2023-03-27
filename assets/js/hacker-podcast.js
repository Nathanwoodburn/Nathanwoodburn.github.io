const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ/.?!@#$%^&*()_+";

let interval = null;
let interval2 = null;
let interval3 = null;


document.querySelector(".copyright").onmouseover = event => {  
    let iteration2 = 0;
    let old2 = "Copyright © Nathan Woodburn 2023";
    clearInterval(interval2);
    
    interval2 = setInterval(() => {
      event.target.innerText = event.target.innerText
        .split("")
        .map((letter, index2) => {
          if(index2 < iteration2) {
            return old2[index2];
          }
        
          return letters[Math.floor(Math.random() * 41)]
        })
        .join("");
      
      if(iteration2 >= old2.length){ 
        clearInterval(interval2);
      }
      
      iteration2 += 1/3;
    }, 10);
  }