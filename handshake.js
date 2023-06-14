if (window.location.hostname != document.currentScript.getAttribute('domain')){
	window.location.href = "https://" + document.currentScript.getAttribute('domain') + window.location.pathname + window.location.search + window.location.hash;
}
else{
	console.log("Already Redirected");
}
