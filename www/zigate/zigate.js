///version:3;

// Check for the various File API support.
if (window.File && window.FileReader && window.FileList && window.Blob) {
    // Great success! All the File APIs are supported.
} else {
    alert('The File APIs are not fully supported in this browser.');
}

var ReportsFolder = location.origin + '/templates/zigate/reports/';
var ConfFolder = location.origin + '/templates/zigate/conf/';
var HwIDX = "";
var DeviceIEEE = new Object();
var Devices;
var LQIlist = new Object();
var LQIdata = new Object();
var NETlist = new Object();
var NETdata = new Object();
var MatrixId = new Object();
var Matrix = new Object();
var orderlist;
var OutResultLinks = "";
var OutResultContents = "";
var NetworkFiles;

function GetDevs(id) {
    $.getJSON($.domoticzurl + "/json.htm", {
            type: "devices",
            format: "json"
        },
        function(DEVdata) {
            var txtdev = "Pas de devices sur le HwID : " + id;
            var tempDevicesList = '{ "ListOfDevices" : [';
            var ii = 0;
            if (typeof DEVdata.result != 'undefined') {
                //txt = '</div><div id="TabDevices" class="tabcontent">';
                txt = '<table id=Devices_Tab border=1><tr><th>Devices ID</th><th>Devices Name</th><th>Devices IEEE</th></tr>';
                $.each(DEVdata.result, function(i, itemDEV) {
                    if (itemDEV.HardwareID == id) {
                        if (CheckIfDeviceInList(itemDEV.ID) == false) {
                            txt += "<tr><td>" + itemDEV.idx + "</td><td>" + itemDEV.Name + "</td><td>" + itemDEV.ID + "</td></tr>";
                            txtdev = "Chargement terminé, selectionner votre fichier LQI_report";
                            DeviceIEEE[ii] = itemDEV.ID;
                            ii++;
                            if (tempDevicesList.length < 30) {
                                tempDevicesList += '{ "id" : "' + itemDEV.idx + '", "name" : "' + itemDEV.Name + '", "IEEE" : "' + itemDEV.ID + '"}';
                            }
                        }
                    }
                });
                tempDevicesList += "]}";
                Devices = JSON.parse(tempDevicesList);
                txt += "</table>";
            }
            $('#ZigateHwLoad').html(txt);

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


function DrawTable(date, data, id) {
    OutResultContents += '<div id="LQI-' + id + '_' + date + '" class="tabcontent2"><div id="LQItab">';
    OutResultContents += "<br><H2>" + date + "</H2><table id=LQI_Tab border=1><tr><th>Devices ID</th>";
    console.log('draw table ' + date + '_' + id);
    MatrixId[date] = '[';
    for (i = 0; i < Object.keys(LQIlist).length; i++) {
        if (i > 0) {
            MatrixId[date] += ",";
        }
        OutResultContents += "<th>" + LQIlist[orderlist[i][0]] + "</th>";
        //MatrixId[i] = LQIlist[orderlist[i][0]];
        MatrixId[date] += '{ "name" :"' + LQIlist[orderlist[i][0]] + '", "color" : "#' + Math.floor(Math.random() * 16777215).toString(16) + '"}';
    }
    MatrixId[date] += "]";
    OutResultContents += "</tr>";
    Matrix[date] = "[";
    for (i = 0; i < Object.keys(LQIlist).length; i++) {
        if (i > 0) {
            Matrix[date] += ",";
        }
        Matrix[date] += "[";
        OutResultContents += "<tr>";
        OutResultContents += "<th>" + LQIlist[orderlist[i][0]] + "</th>";
        //console.log("Short adress search (line) : " + LQIlist[i])
        for (ii = 0; ii < Object.keys(LQIlist).length; ii++) {
            //console.log("Short adress search (row) : " + LQIlist[ii])
            if (ii > 0) {
                Matrix[date] += ",";
            }
            if (LQIlist[orderlist[i][0]] == LQIlist[orderlist[ii][0]]) {
                OutResultContents += "<th bgcolor='black'>O</th>";
                Matrix[date] += "0";
            } else if (LQIlist[orderlist[ii][0]] in data[LQIlist[orderlist[i][0]]]) {
                OutResultContents += "<th bgcolor='green'>Y</th>";
                Matrix[date] += "1";
            } else if (LQIlist[orderlist[i][0]] in data[LQIlist[orderlist[ii][0]]]) {
                OutResultContents += "<th bgcolor='green'>Y</th>";
                Matrix[date] += "1";
            } else {
                OutResultContents += "<th bgcolor='red'>X</th>";
                Matrix[date] += "0";
            };
        };
        OutResultContents += "</tr>";
        Matrix[date] += "]";
    };
    OutResultContents += "</table>";
    Matrix[date] += "]";
};

function DrawGraph(date, data, id) {
    OutResultContents += '<div id="GraphFile_' + id + '_' + date + '"><br>';
    OutResultContents += '<output id="LQI_' + id + '_' + date + '"></output></div></div>';
    console.log('draw LQI graph ' + date + '_' + id);
};

function DrawNetGraph(date, data, id) {
    OutResultContents += '<div id="NET-' + id + '_' + date + '" class="tabcontent3"><div id="Nettab">';
    OutResultContents += '<div id="GraphFile_' + id + '_' + date + '"><br>';
    OutResultContents += '<output id="NET_' + id + '_' + date + '"></output></div></div>';
    console.log('draw net graph ' + date + '_' + id);
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

function openTab2(evt, TabName) {
    // Declare all variables
    var i, tabcontent, tablinks;

    // Get all elements with class="tabcontent" and hide them
    tabcontent = document.getElementsByClassName("tabcontent2");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }

    // Get all elements with class="tablinks" and remove the class "active"
    tablinks = document.getElementsByClassName("tablinks2");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }

    // Show the current tab, and add an "active" class to the button that opened the tab
    document.getElementById(TabName).style.display = "block";
    evt.currentTarget.className += " active";
}

function openTab3(evt, TabName) {
    // Declare all variables
    var i, tabcontent, tablinks;

    // Get all elements with class="tabcontent" and hide them
    tabcontent = document.getElementsByClassName("tabcontent3");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }

    // Get all elements with class="tablinks" and remove the class "active"
    tablinks = document.getElementsByClassName("tablinks3");
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


function readTXT(file, id, type) {
    console.log('file read is : ' + file)
    $.get({
        url: file,
        dataType: "text",
        success: function(data) {
            if (type == 'LQI') {
                readLQI(id, data);
                PrintLQIGraph(id);
            }
            if (type == 'Conf') {
                readConf(id, data);
            }
            if (type == 'Network') {
                readNetwork(id, data);
                //PrintNETGraph(id);
            }
        }
    });
};

function readLQI(id, data) {
    // Closure to capture the file information.
    const allLines = data.split(/\r\n|\n/); // Reading line by line 
    allLines.map((line) => {
        if (line.replace(/ /g, '') != '') {
            LQIdate = line.slice(2, 11);
            console.log('LQI reports date : ' + LQIdate)
            LQIdata[LQIdate] = JSON.parse(line.slice(14, line.length - 1).replace(/ /g, '').replace(/'/g, '"').replace(/True/g, '"True"').replace(/False/g, '"False"'));
            console.log('LQI reports data :' + LQIdata[LQIdate]);
            LQIlist = Object.keys(LQIdata[LQIdate]);
            // Make Table
            orderlist = sortProperties(LQIlist);
            //OutResultContents += '<div class="tabcontent2">';
            DrawTable(LQIdate, LQIdata[LQIdate], id);
            DrawGraph(LQIdate, LQIdata[LQIdate], id);
            OutResultContents += '</div>';
            console.log('Next reports (line)');
        };
    });
    OutResultLinks += "<div class='LQItab'>"

    for (ii = 0; ii < Object.keys(LQIdata).length; ii++) {
        var datelist = Object.keys(LQIdata);
        OutResultLinks += '<button class="tablinks2" onclick="openTab2(event,`LQI-' + id + '_' + datelist[ii] + '`)">' + id + '_' + datelist[ii] + '</button>';
    }
    OutResultLinks += "</div>"
        //Print Out result
    $('#LQIResult').html(OutResultLinks + OutResultContents);
    //PrintGraph(id);
}

function readNetwork(id, data) {

    console.log('Network read');
    // Closure to capture the file information.
    const allLines = data.split(/\r\n|\n/); // Reading line by line 
    allLines.map((line) => {
        if (line.replace(/ /g, '') != '') {
            NETdate = line.slice(2, 11);
            console.log('Network scan reports date : ' + LQIdate)
            NETdata[NETdate] = JSON.parse(line.slice(14, line.length - 1).replace(/ /g, '').replace(/'/g, '"').replace(/True/g, '"True"').replace(/False/g, '"False"'));
            console.log('Network scan reports data :' + NETdata[NETdate]);
            NETlist = Object.keys(NETdata[NETdate]);
            DrawNetGraph(NETdate, NETdata[NETdate], id);
            OutResultContents += '</div>';
            console.log('Next reports (line)');
        };
    });
    OutResultLinks += "<div class='NETtab'>"

    for (ii = 0; ii < Object.keys(NETdata).length; ii++) {
        var datelist = Object.keys(NETdata);
        OutResultLinks += '<button class="tablinks3" onclick="openTab3(event,`NET-' + id + '_' + datelist[ii] + '`)">' + id + '_' + datelist[ii] + '</button>';
    }
    OutResultLinks += "</div>"
        //Print Out result
    $('#NetResult').html(OutResultLinks + OutResultContents);



}

function readConf(id, data) {

    console.log('Conf read');
    // Closure to capture the file information.
    const allLines = data.split(/\r\n|\n/); // Reading line by line 

    //Print Out result
    $('#ZigateConf').html(allLines);


}


function LQIGraph(id, date, matriX, matrixid) {

    var width = 720,
        height = 720,
        outerRadius = Math.min(width, height) / 2 - 10,
        innerRadius = outerRadius - 24;

    var formatPercent = d3.format(".1%");

    console.log('d3.select : LQI_' + id + '_' + date);
    var svg = d3.select('#LQI_' + id + '_' + date).append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("id", "circle")
        .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

    var arc = d3.svg.arc()
        .innerRadius(innerRadius)
        .outerRadius(outerRadius);

    var layout = d3.layout.chord()
        .padding(.04)
        .sortSubgroups(d3.descending)
        .sortChords(d3.ascending);

    var path = d3.svg.chord()
        .radius(innerRadius);

    svg.append("circle")
        .attr("r", outerRadius);

    // Compute the chord layout.
    matrix = JSON.parse(matriX);
    IEEE = JSON.parse(matrixid);
    //console.log('Graph(' + id + ', ' + date + ', ' + matrix + ', ' + IEEE + ')');
    console.log('Load matrix ok ');
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

function NETGraph(id, date, matriX) {

    data = (await require("@observablehq/alphabet"))
        .slice()
        .sort((a, b) => b.frequency - a.frequency)
        .map(({ letter, frequency }) => ({ name: letter, value: frequency }))

    const svg = d3.select(DOM.svg(width, height));

    svg.append("g")
        .attr("fill", "steelblue")
        .selectAll("rect").data(data).enter().append("rect")
        .attr("x", d => x(d.name))
        .attr("y", d => y(d.value))
        .attr("height", d => y(0) - y(d.value))
        .attr("width", x.bandwidth());

    svg.append("g")
        .call(xAxis);

    svg.append("g")
        .call(yAxis);
}

function n(n) {
    return n > 9 ? "" + n : "0" + n;
}

function PrintLQIGraph(id) {
    console.log('Print Graph :' + id + ', data : ' + LQIdata);
    for (ii = 0; ii < Object.keys(LQIdata).length; ii++) {
        var datelist = Object.keys(LQIdata);
        console.log("Graph for :" + id + ', date : ' + datelist[ii]);
        //console.log('Graph(' + id + ',' + datelist[ii] + ', ' + Matrix[datelist[ii]] + ',' + MatrixId[datelist[ii]] + ');');
        LQIGraph(id, datelist[ii], Matrix[datelist[ii]], MatrixId[datelist[ii]]);
    }
}

function PrintNETGraph(id) {
    console.log('Print Graph :' + id + ', data : ' + LQIdata);
    for (ii = 0; ii < Object.keys(NETdata).length; ii++) {
        var datelist = Object.keys(NETdata);
        console.log("Graph for :" + id + ', date : ' + datelist[ii]);
        //console.log('Graph(' + id + ',' + datelist[ii] + ', ' + Matrix[datelist[ii]] + ',' + MatrixId[datelist[ii]] + ');');
        NETGraph(id, datelist[ii], NETdata[datelist[ii]]);
    }
}

function ReadHxIDx() {
    $.domoticzurl = ""; //"http://localhost:8080";
    $.getJSON($.domoticzurl + "/json.htm", {
            type: "hardware",
            format: "json"
        },
        function(HWdata) {
            var txtHW = "Zigate absente";
            if (typeof HWdata.result != 'undefined') {
                $.each(HWdata.result, function(i, item) {
                    if (item.Extra == 'Zigate') {
                        HwIDX = n(item.idx);
                        txtHW = "HwID : " + HwIDX;
                    }
                });
            }
            //console.log(txtHW);
            $('#ZigateHwLoad').html(txtHW);
            NetworkFile = 'Network_scan-' + HwIDX + '.txt.json';
            LQIFile = 'LQI_reports-' + HwIDX + '.txt.json';
            ConfFile = 'PluginConf-' + HwIDX + '.txt';
            GetDevs(HwIDX);
            readTXT(ReportsFolder + LQIFile, HwIDX, "LQI");
            readTXT(ReportsFolder + NetworkFile, HwIDX, "Network");
            readTXT(ConfFolder + ConfFile, HwIDX, "Conf");

        });
};


$(document).ready(function() {
    ReadHxIDx();
});