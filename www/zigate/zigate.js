// Check for the various File API support.
if (window.File && window.FileReader && window.FileList && window.Blob) {
    // Great success! All the File APIs are supported.
} else {
    alert('The File APIs are not fully supported in this browser.');
}


var HwIDX;
var DeviceIEEE = new Object();
var Devices;
var LQIlist = new Object();
var LQIdata = new Object();
var MatrixId;
var Matrix;
var orderlist;
var OutResultLinks = "";
var OutResultContents = "";


function GetHWId() {
    $.getJSON($.domoticzurl + "/json.htm", {
            type: "hardware",
            format: "json"
        },
        function(HWdata) {
            var txtHW = "Zigate absente";
            if (typeof HWdata.result != 'undefined') {
                $.each(HWdata.result, function(i, item) {
                    if (item.Extra == 'Zigate') {
                        HwIDX = item.idx;
                        txtHW = "HwID : " + HwIDX;
                    }
                });
            }
            $('#ZigateHwLoad').html(txtHW);
        });
};

function GetDevs() {
    $.getJSON($.domoticzurl + "/json.htm", {
            type: "devices",
            format: "json"
        },
        function(DEVdata) {
            var txtdev = "Pas de devices sur le HwID : " + HwIDX;
            var tempDevicesList = '{ "ListOfDevices" : [';
            var ii = 0;
            if (typeof DEVdata.result != 'undefined') {
                OutResultContents = '</div><div id="TabDevices" class="tabcontent">'
                OutResultContents += '<table border=1><tr><th>Devices ID</th><th>Devices Name</th><th>Devices IEEE</th></tr>';
                $.each(DEVdata.result, function(i, itemDEV) {
                    if (itemDEV.HardwareID == HwIDX) {
                        if (CheckIfDeviceInList(itemDEV.ID) == false) {
                            OutResultContents += "<tr><td>" + itemDEV.idx + "</td><td>" + itemDEV.Name + "</td><td>" + itemDEV.ID + "</td></tr>";
                            txtdev = "Chargement terminé, selectionner votre fichier LQI_report"
                            DeviceIEEE[ii] = itemDEV.ID;
                            ii++;
                            if (tempDevicesList.length < 30)
                                tempDevicesList += '{ "id" : "' + itemDEV.idx + '", "name" : "' + itemDEV.Name + '", "IEEE" : "' + itemDEV.ID + '"}';
                        }
                    }
                });
                tempDevicesList += "]}";
                Devices = JSON.parse(tempDevicesList);
                OutResultContents += "</table></div>";
            }
            $('#ZigateHwLoad').html(txtdev);

        });
};

function CheckIfDeviceInList(IEEE) {
    var i;
    var bool = false;
    for (i = 0; i < Object.keys(DeviceIEEE).length; i++) {
        if (DeviceIEEE[i] == IEEE) {
            bool = true;
        }
    }
    return bool;

};


function DrawTable(k) {
    var txtdev;
    txtdev = '<div id="TabFile_' + k + '" class="tabcontent">';
    txtdev += "<table border=1><tr><th>Devices ID</th>";
    MatrixId = '[';
    for (i = 0; i < Object.keys(LQIlist).length; i++) {
        if (i > 0) {
            MatrixId += ",";
        }
        txtdev += "<th>" + LQIlist[orderlist[i][0]] + "</th>";
        //MatrixId[i] = LQIlist[orderlist[i][0]];
        MatrixId += '{ "name" :"' + LQIlist[orderlist[i][0]] + '", "color" : "#' + LQIlist[orderlist[i][0]] + '"}';
    }
    MatrixId += "]";
    txtdev += "</tr>";
    Matrix = "[";
    for (i = 0; i < Object.keys(LQIlist).length; i++) {
        if (i > 0) {
            Matrix += ",";
        }
        Matrix += "[";
        txtdev += "<tr>";
        txtdev += "<th>" + LQIlist[orderlist[i][0]] + "</th>";
        console.log("Short adress search (line) : " + LQIlist[i])
        for (ii = 0; ii < Object.keys(LQIlist).length; ii++) {
            console.log("Short adress search (row) : " + LQIlist[ii])
            if (ii > 0) {
                Matrix += ",";
            }
            if (LQIlist[orderlist[i][0]] == LQIlist[orderlist[ii][0]]) {
                txtdev += "<th bgcolor='black'>O</th>";
                Matrix += "0";
            } else if (LQIlist[orderlist[ii][0]] in LQIdata[LQIlist[orderlist[i][0]]]) {
                txtdev += "<th bgcolor='green'>Y</th>";
                Matrix += "1";
            } else if (LQIlist[orderlist[i][0]] in LQIdata[LQIlist[orderlist[ii][0]]]) {
                txtdev += "<th bgcolor='green'>Y</th>";
                Matrix += "1";
            } else {
                txtdev += "<th bgcolor='red'>X</th>";
                Matrix += "0";
            };
        };
        txtdev += "</tr>";
        Matrix += "]";
    };
    txtdev += "</table></div>";
    Matrix += "]";
    OutResultContents += txtdev;
};

function DrawGraph(j) {
    var txtdev;
    txtdev = '<div id="GraphFile_' + j + '" class="tabcontent">';
    txtdev += '<output id="networkchart"></output>';
    OutResultContents += txtdev;
};


function openTab(evt, TabName) {
    // Declare all variables
    var i, tabcontent, tablinks;

    // Get all elements with class="tabcontent" and hide them
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }

    // Get all elements with class="tablinks" and remove the class "active"
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }

    // Show the current tab, and add an "active" class to the button that opened the tab
    document.getElementById(TabName).style.display = "block";
    evt.currentTarget.className += " active";
}


function sortProperties(obj) {
    // convert object into array
    var sortable = [];
    for (var key in obj)
        if (obj.hasOwnProperty(key))
            sortable.push([key, obj[key]]); // each item is an array in format [key, value]

        // sort items by value
    sortable.sort(function(a, b) {
        var x = a[1].toLowerCase(),
            y = b[1].toLowerCase();
        return x < y ? -1 : x > y ? 1 : 0;
    });
    return sortable; // array in format [ [ key1, val1 ], [ key2, val2 ], ... ]
}


function handleFileSelect(evt) {
    evt.stopPropagation();
    evt.preventDefault();

    var files = evt.dataTransfer.files; // FileList object.
    var reader = new FileReader();

    var II = 0;
    OutResultLinks = '<div class="tab">';
    OutResultLinks += '<button class="tablinks" onclick="openTab(event, `TabDevices`)">Devices</button>';
    for (var i = 0, f; f = files[i]; i++) {
        // Closure to capture the file information.
        reader.onload = (event) => {
            //LQIlst = '['
            const file = event.target.result;
            const allLines = file.split(/\r\n|\n/); // Reading line by line 
            allLines.map((line) => {
                //console.log('next line');
                if (line.replace(/ /g, '') != '') {
                    LQIlist[II] = line.slice(0, 4);
                    //LQIlst += "{'shID':'" + line.slice(0, 4) + "'},";
                    //console.log('LQI :' + LQIlist[II])
                    LQIdata[LQIlist[II]] = JSON.parse(line.slice(6).replace(/ /g, '').replace(/'/g, '"').replace(/True/g, '"True"').replace(/False/g, '"False"'));
                    //console.log('LQI data :' + LQIdata[LQIlist[II]])
                    II++;
                    //} else {
                    //    LQIlst += LQIlst.slice(-1) + "]"
                };
            });
            // Make Table
            orderlist = sortProperties(LQIlist);
            OutResultLinks += '<button class="tablinks" onclick="openTab(event, `TabFile_' + i + '`)">TabFile' + i + '</button>';
            OutResultLinks += '<button class="tablinks" onclick="openTab(event, `GraphFile_' + i + '`)">GraphFile' + i + '</button>';
            DrawTable(i);
            DrawGraph(i);
            OutResultLinks += '</div>';
            //Print Out result
            $('#Result').html(OutResultLinks + OutResultContents);
            //$('#Result').html(OutResultContents);
            Graph();
        };
        reader.onerror = (evt) => {
            alert(evt.target.error.name);
        };
        reader.readAsText(f);
    }

}


function Graph() {

    var width = 720,
        height = 720,
        outerRadius = Math.min(width, height) / 2 - 10,
        innerRadius = outerRadius - 24;

    var formatPercent = d3.format(".1%");

    var arc = d3.svg.arc()
        .innerRadius(innerRadius)
        .outerRadius(outerRadius);

    var layout = d3.layout.chord()
        .padding(.04)
        .sortSubgroups(d3.descending)
        .sortChords(d3.ascending);

    var path = d3.svg.chord()
        .radius(innerRadius);

    var svg = d3.select("#networkchart").append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("id", "circle")
        .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

    svg.append("circle")
        .attr("r", outerRadius);

    matrix = JSON.parse(Matrix);
    IEEE = JSON.parse(MatrixId);
    // Compute the chord layout.
    layout.matrix(matrix);

    // Add a group per neighborhood.
    var group = svg.selectAll(".group")
        .data(layout.groups)
        .enter().append("g")
        .attr("class", "group")
        .on("mouseover", mouseover);

    // Add a mouseover title.
    // group.append("title").text(function(d, i) {
    // return IEEE[i].name + ": " + formatPercent(d.value) + " of origins";
    // });

    // Add the group arc.
    var groupPath = group.append("path")
        .attr("id", function(d, i) { return "group" + i; })
        .attr("d", arc)
        .style("fill", function(d, i) { return IEEE[i].color; });

    // Add a text label.
    var groupText = group.append("text")
        .attr("x", 6)
        .attr("dy", 15);

    groupText.append("textPath")
        .attr("xlink:href", function(d, i) { return "#group" + i; })
        .text(function(d, i) { return IEEE[i].name; });

    // Remove the labels that don't fit. :(
    groupText.filter(function(d, i) { return groupPath[0][i].getTotalLength() / 2 - 16 < this.getComputedTextLength(); })
        .remove();

    // Add the chords.
    var chord = svg.selectAll(".chord")
        .data(layout.chords)
        .enter().append("path")
        .attr("class", "chord")
        .style("fill", function(d) { return IEEE[d.source.index].color; })
        .attr("d", path);

    // Add an elaborate mouseover title for each chord.
    chord.append("title").text(function(d) {
        return IEEE[d.source.index].name +
            " → " + IEEE[d.target.index].name +
            ": " + formatPercent(d.source.value) +
            "\n" + IEEE[d.target.index].name +
            " → " + IEEE[d.source.index].name +
            ": " + formatPercent(d.target.value);
    });

    function mouseover(d, i) {
        chord.classed("fade", function(p) {
            return p.source.index != i &&
                p.target.index != i;
        });
    }

}

function handleDragOver(evt) {
    evt.stopPropagation();
    evt.preventDefault();
    evt.dataTransfer.dropEffect = 'copy'; // Explicitly show this is a copy.
}


$(document).ready(function() {
    $.domoticzurl = ""; //"http://localhost:8080";
    GetHWId();
    GetDevs();
});

// Setup the dnd listeners.
var dropZone = document.getElementById('drop_zone');
dropZone.addEventListener('dragover', handleDragOver, false);
dropZone.addEventListener('drop', handleFileSelect, false);