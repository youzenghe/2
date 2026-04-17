// 全局变量
var margin = {top: 20, right: 120, bottom: 20, left: 120},
    width = 1500 - margin.right - margin.left,
    height = 800 - margin.top - margin.bottom;

var i = 0,
    duration = 750,
    root,
    myData = null,
    nodeMap = {};

var tree = d3.layout.tree()
    .size([height, width]);

var diagonal = d3.svg.diagonal()
    .projection(function (d) {
        return [d.y, d.x];
    });

var svg = d3.select("#graph-svg")
    .attr("width", width + margin.right + margin.left)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var tooltip = d3.select("#tooltip");
var notification = d3.select("#notification");
var currentScale = 1;

// 初始化
document.addEventListener("DOMContentLoaded", function() {
    loadData();
    setupEventListeners();
});

function loadData() {
    showLoader();

    d3.json("data.json", function(error, data) {
        if (error) {
            console.error("加载错误:", error);
            hideLoader();
            showNotification("加载失败: " + error, "error");
            return;
        }

        try {
            // 验证数据格式
            if (!data || !data.children || !Array.isArray(data.children)) {
                throw new Error("数据格式不正确");
            }

            // 处理数据
            processData(data);

            // 初始化视图
            initializeView();

            hideLoader();
            showNotification("数据加载成功", "success");
        } catch (e) {
            console.error("数据处理错误:", e);
            hideLoader();
            showNotification("数据处理失败: " + e.message, "error");
        }
    });
}
function processData(data) {
    // 确保数据格式正确
    if (!data.name) data.name = "法律集合";
    if (!data.children) data.children = [];

    // 处理每个节点
    function processNode(node) {
        if (!node.lines && node.name && node.name.match(/第[零一二三四五六七八九十百]+条/)) {
            node.lines = node.name;
        }

        if (node.children) {
            node.children.forEach(processNode);
        }
    }

    data.children.forEach(processNode);
    myData = data;
}

function initializeView() {
    // 初始化节点映射
    nodeMap = {};
    buildNodeMap(myData);

    // 默认展开第一层
    if (myData.children && myData.children.length > 0) {
        myData.children.forEach(function(child) {
            if (child.children) {
                child._children = child.children;
                child.children = null;
            }
        });

        root = myData;
        root.x0 = height / 2;
        root.y0 = 0;

        update(root);
        add(myData.children.map(d => d.name));
        updateResultStats(myData.children.length);
    }
}

function buildNodeMap(node) {
    if (!node) return;

    nodeMap[node.name] = node;
    if (node.children) {
        node.children.forEach(buildNodeMap);
    }
    if (node._children) {
        node._children.forEach(buildNodeMap);
    }
}

function setupEventListeners() {
    var searchBtn = document.getElementById('searchBtn');
    var searchText = document.getElementById('searchText');

    searchBtn.addEventListener("click", search);
    searchText.addEventListener("keypress", function (event) {
        if (event.keyCode === 13) {
            search();
        }
    });

    searchText.addEventListener("input", function() {
        if (this.value.length === 0) {
            resetSearch();
        }
    });
}

function update(source) {
    var nodes = tree.nodes(root).reverse();
    var links = tree.links(nodes);

    // 优化节点位置
    nodes.forEach(function(d) {
        d.y = d.depth * 200 + (d.children || d._children ? 150 : 50);
    });

    var node = svg.selectAll("g.node")
        .data(nodes, function(d) { return d.id || (d.id = ++i); });

    // 进入节点
    var nodeEnter = node.enter().append("g")
        .attr("class", "node")
        .attr("transform", function(d) {
            return "translate(" + source.y0 + "," + source.x0 + ")";
        })
        .on("click", click)
        .on("mouseover", mouseover)
        .on("mouseout", mouseout);

    // 添加圆形
    nodeEnter.append("circle")
        .attr("r", 1e-6)
        .attr("class", function(d) {
            return (d._children ? "collapsed" : "") +
                (d.children || d._children ? " expand-collapse" : "");
        })
        .style("fill", function(d) {
            return getNodeColor(d);
        });

    // 添加展开/折叠指示器
    nodeEnter.filter(function(d) { return d.children || d._children; })
        .append("text")
        .attr("class", "expand-icon")
        .attr("x", 8)
        .attr("dy", ".35em")
        .attr("text-anchor", "start")
        .text(function(d) { return d.children ? "-" : "+"; });

    // 添加节点文本
    nodeEnter.append("text")
        .attr("x", function(d) {
            return (d.children || d._children) ? -18 : 18;
        })
        .attr("dy", ".35em")
        .attr("text-anchor", function(d) {
            return (d.children || d._children) ? "end" : "start";
        })
        .text(function(d) { return d.name; });

    // 更新节点
    var nodeUpdate = node.transition()
        .duration(duration)
        .attr("transform", function(d) {
            return "translate(" + d.y + "," + d.x + ")";
        });

    nodeUpdate.select("circle")
        .attr("r", 6)
        .attr("class", function(d) {
            return (d._children ? "collapsed" : "") +
                (d.children || d._children ? " expand-collapse" : "");
        })
        .style("fill", function(d) {
            return getNodeColor(d);
        })
        .style("stroke-width", function(d) {
            return d === root ? "2px" : "1.5px";
        });

    nodeUpdate.select(".expand-icon")
        .text(function(d) { return d.children ? "-" : "+"; });

    nodeUpdate.select("text")
        .style("font-weight", function(d) {
            return d === root ? "bold" : "normal";
        });

    // 退出节点
    var nodeExit = node.exit().transition()
        .duration(duration)
        .attr("transform", function(d) {
            return "translate(" + source.y + "," + source.x + ")";
        })
        .remove();

    nodeExit.select("circle")
        .attr("r", 1e-6);

    nodeExit.select("text")
        .style("fill-opacity", 1e-6);

    // 更新连线
    var link = svg.selectAll("path.link")
        .data(links, function(d) { return d.target.id; });

    link.enter().insert("path", "g")
        .attr("class", "link")
        .attr("d", function(d) {
            var o = {x: source.x0, y: source.y0};
            return diagonal({source: o, target: o});
        });

    link.transition()
        .duration(duration)
        .attr("d", diagonal);

    link.exit().transition()
        .duration(duration)
        .attr("d", function(d) {
            var o = {x: source.x, y: source.y};
            return diagonal({source: o, target: o});
        })
        .remove();

    // 保存位置
    nodes.forEach(function(d) {
        d.x0 = d.x;
        d.y0 = d.y;
    });
}

function getNodeColor(d) {
    if (d === root) return "#e74c3c";
    if (d._children) return "#f0ead6";
    if (d.children) return "#fff";
    return "#3498db";
}

function click(d) {
    if (d.children) {
        d._children = d.children;
        d.children = null;
    } else {
        d.children = d._children;
        d._children = null;
    }

    // 添加平滑过渡
    svg.transition()
        .duration(duration)
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")scale(" + currentScale + ")");

    update(d);
}

function mouseover(d) {
    if (d._children == null && d.children == null && d.lines) {
        tooltip.html(d.lines)
            .style("left", (d3.event.pageX + 10) + "px")
            .style("top", (d3.event.pageY + 10) + "px")
            .style("opacity", 0.9);
    }

    // 高亮当前节点和连接线
    d3.select(this).select("circle").style("stroke", "#e74c3c");
    svg.selectAll(".link")
        .filter(function(l) { return l.source === d || l.target === d; })
        .style("stroke", "#e74c3c")
        .style("stroke-width", "2px");
}

function mouseout(d) {
    tooltip.style("opacity", 0);

    // 恢复默认样式
    d3.select(this).select("circle").style("stroke", "#2980b9");
    svg.selectAll(".link")
        .style("stroke", "#bdc3c7")
        .style("stroke-width", "1.5px");
}

function search() {
    var text = document.getElementById('searchText').value.trim();

    if (text.length === 0) {
        showNotification("请输入搜索内容", "warning");
        return;
    }

    var matchedLaws = [];
    var matchCount = 0;

    function traverse(node) {
        if (node.children) {
            node.children.forEach(traverse);
        }
        if (node._children) {
            node._children.forEach(traverse);
        }
        if (node.name && node.name.includes(text)) {
            matchedLaws.push(node.name);
            matchCount++;
        }
        if (node.lines && node.lines.includes(text)) {
            if (!matchedLaws.includes(node.name)) {
                matchedLaws.push(node.name);
            }
            matchCount++;
        }
    }

    traverse(myData);

    // 去重
    matchedLaws = [...new Set(matchedLaws)];

    if (matchedLaws.length === 0) {
        showNotification("未找到匹配的法律条文", "info");
        return;
    }

    deleteAll();
    add(matchedLaws);
    updateResultStats(matchedLaws.length, matchCount);
    highlightSearchText(text);
}

function highlightSearchText(text) {
    svg.selectAll("text").each(function(d) {
        var el = d3.select(this);
        var content = el.text();
        if (content.includes(text)) {
            var html = content.replace(new RegExp(text, "g"), "<tspan class='highlight'>" + text + "</tspan>");
            el.html(html);
        }
    });
}

function resetSearch() {
    deleteAll();
    add(myData.children.map(d => d.name));
    updateResultStats(myData.children.length);

    // 移除高亮
    svg.selectAll("text").each(function() {
        var el = d3.select(this);
        el.text(el.text());
    });
}

function deleteAll() {
    var s = document.getElementById('sideul');
    while (s.firstChild) {
        s.removeChild(s.firstChild);
    }
}

function add(laws) {
    var s = document.getElementById('sideul');
    laws.forEach(function(law) {
        var li = document.createElement("li");
        li.textContent = law;
        li.addEventListener("click", function() {
            // 移除之前的高亮
            var activeItems = document.querySelectorAll('#sideul li.active');
            activeItems.forEach(function(item) {
                item.classList.remove('active');
            });

            // 添加新的高亮
            this.classList.add('active');

            // 找到匹配的节点
            var matchedNode = nodeMap[law];
            if (matchedNode) {
                // 展开路径
                expandPath(matchedNode);
                // 定位到该节点
                root = matchedNode;
                root.x0 = height / 2;
                root.y0 = 400;
                update(root);

                // 平滑滚动到视图
                var nodeElement = svg.selectAll(".node").filter(function(d) { return d === root; });
                if (!nodeElement.empty()) {
                    var transform = d3.transform(nodeElement.attr("transform"));
                    var x = transform.translate[1];
                    var y = transform.translate[0];

                    svg.transition()
                        .duration(1000)
                        .attr("transform", "translate(" + margin.left + "," + (margin.top - x + height/2) + ")scale(" + currentScale + ")");
                }
            }
        });
        s.appendChild(li);
    });
}

function expandPath(node) {
    if (node.parent) {
        expandPath(node.parent);
        if (node.parent._children) {
            node.parent.children = node.parent._children;
            node.parent._children = null;
        }
    }
}

function updateResultStats(total, matches) {
    var stats = document.getElementById('resultStats');
    if (matches !== undefined) {
        stats.innerHTML = `找到 ${total} 条相关法律 (${matches} 处匹配)`;
    } else {
        stats.innerHTML = `共 ${total} 条法律`;
    }
}

function toggleSidebar() {
    var aside = document.querySelector('aside');
    var controls = document.querySelector('.sidebar-controls');

    aside.classList.toggle('collapsed');

    // 更新按钮图标
    var toggleBtn = document.querySelector('.toggle-btn i');
    if (aside.classList.contains('collapsed')) {
        toggleBtn.className = 'fas fa-chevron-right';
    } else {
        toggleBtn.className = 'fas fa-chevron-left';
    }
}

function zoomIn() {
    currentScale *= 1.2;
    svg.transition()
        .duration(300)
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")scale(" + currentScale + ")");
}

function zoomOut() {
    currentScale *= 0.8;
    svg.transition()
        .duration(300)
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")scale(" + currentScale + ")");
}

function resetZoom() {
    currentScale = 1;
    svg.transition()
        .duration(750)
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")scale(1)");
}

function showNotification(message, type) {
    notification.text(message)
        .attr("class", "notification " + type)
        .transition()
        .duration(300)
        .style("opacity", 1);

    setTimeout(function() {
        notification.transition()
            .duration(300)
            .style("opacity", 0);
    }, 3000);
}

function showLoader() {
    d3.select(".loader").style("display", "flex");
}

function hideLoader() {
    d3.select(".loader").style("display", "none");
}

function jumpToURL() {
    window.location.href = "http://127.0.0.1:5000/dashboard";
}