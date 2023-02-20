codetarget = document.querySelector(".skillcode");

// C# Code
document.querySelector(".programc").onmouseover = event => {  
    codetarget.innerText = "if(c#.hover){\nthis.show();\n}\nelse{\nthis.hide;\n}";
};
document.querySelector(".programc").onmouseleave = event => {  
    codetarget.innerText = "";
};

// Linux Code
document.querySelector(".programlinux").onmouseover = event => {  
    codetarget.innerText = "#!/bin/bash\nif [ $1 == \"linux\" ]; then\n    echo \"Linux is awesome!\";\nelse\n    echo \"Linux is still cool!\";\nfi";
};
document.querySelector(".programlinux").onmouseleave = event => {  
    codetarget.innerText = "";
};

// Nginx Code
document.querySelector(".programnginx").onmouseover = event => {  
    codetarget.innerText = "server {\n    listen 80;\n    server_name nathan.woodburn;\n    location / {\n        root /var/www/nathanwoodburn;\n        index index.html;\n}\nlisten 443 ssl;\nssl_certificate /etc/ssl/nathanwoodburn.crt;\nssl_certificate_key /etc/ssl/nathanwoodburn.key;\n}";
};
document.querySelector(".programnginx").onmouseleave = event => {  
    codetarget.innerText = "";
};