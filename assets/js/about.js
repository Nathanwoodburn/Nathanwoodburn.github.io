function slideout() {
    bodydiv = document.querySelector("body");
    bodydiv.style.top = "-100%";
    setTimeout(function() { 
        window.location.href = "/#about"
        bodydiv.style.top = "0px";
    }, 1000)
}


// jQuery(document).ready(function(){
//     function resizeForm(){
//         var width = (window.innerWidth > 0) ? window.innerWidth : document.documentElement.clientWidth;
//         if(width > 1024){

//         } else {

//         }    
//     }
//     window.onresize = resizeForm;
//     resizeForm();
// });

document.addEventListener("scroll", scroll);
function scroll() {
    var width = (window.innerWidth > 0) ? window.innerWidth : document.documentElement.clientWidth;
    if(width > 1024){
        slideout();
    }
}
