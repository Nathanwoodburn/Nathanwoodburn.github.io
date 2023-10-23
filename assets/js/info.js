// On load
onload = function() {
    dockerInfo();
    systemUptime();
    systemLoad();

};



//  On tick
setInterval(function() {
    dockerInfo();
    systemUptime();
    systemLoad();

    console.log("Updated");
}, 1000);

const api = "https://glances.woodburn.au/api/3/";

// Docker info function
function dockerInfo() {
    // Get the containers.name values from the json
    // Replace the interHTML for #containers with the container name
    fetch(api + "docker")
        .then(response => response.json())
        .then(data => {
            // Loop through the containers and get the name and the status
            // Display in a containers running and containers stopped
            let runningContainers = [];
            let stoppedContainers = [];
            for (let i = 0; i < data.containers.length; i++) {
                if (data.containers[i].Status === "running") {
                    runningContainers.push(data.containers[i].name);
                } else {
                    stoppedContainers.push(data.containers[i].name);
                }
            }
            // Create the containersName variable
            let containersName = "Total Containers: " + data.containers.length + "<br>";
            containersName += "Running Containers: " + runningContainers.length + "<br>";
            containersName += "Stopped Containers: " + stoppedContainers.length + "<br><br>";
            // Loop through the running containers and add them to the containersName variable
            
            document.getElementById("containers").innerHTML = containersName;
        })
        .catch(err => console.log(err));
};

// System uptime function
function systemUptime() {
    fetch(api + "uptime")
        .then(response => response.text())
        .then(data => {
            // Get text data remove the quotes
            let uptime = data.replace(/['"]+/g, '');
            document.getElementById("uptime").innerHTML = uptime;
        })
        .catch(err => console.log(err));
};

function systemLoad() {
    fetch(api + "mem").then(response => response.json()).then(data => {
        // Get percentage of memory used
        let memPercent = data.percent + "% RAM";
        document.getElementById("mem").innerHTML = memPercent;
    }).catch(err => console.log(err));

    fetch(api + "cpu").then(response => response.json()).then(data => {
        // Get total CPU used
        let cpuPercent = data.total + "% CPU";
        document.getElementById("cpu").innerHTML = cpuPercent;
    }).catch(err => console.log(err));

    fetch(api + "fs").then(response => response.json()).then(data => {
        // For each file system get percent disk used
        let diskPercent = data[0].percent + "% Disk";
        // Get GB of storage left
        let diskFree = data[0].free;
        // Convert to GB
        diskFree = diskFree / 1000000000;
        // Round to 2 decimal places
        diskFree = diskFree.toFixed(2);
        // Add to the diskPercent variable
        diskPercent += "<br>" + diskFree + " GB Free";
        document.getElementById("disk").innerHTML = diskPercent;
    }).catch(err => console.log(err));
};
