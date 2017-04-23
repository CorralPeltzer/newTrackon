<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>${self.title()}</title>
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
    <link rel="icon" type="image/png" href="/favicon-32x32.png" sizes="32x32">
    <link rel="icon" type="image/png" href="/favicon-16x16.png" sizes="16x16">
    <link rel="manifest" href="/manifest.json">
    <link rel="mask-icon" href="/safari-pinned-tab.svg" color="#25802c">
    <meta name="theme-color" content="#ffffff">
    <link rel="stylesheet" href="/static/css/base.min.css" type="text/css"/>
</head>
<body>
    <div class="container_12">
        <div class="grid_12 headfoot">
            <h1 id="branding"><a href="/"><i><b>newTrackon</b></i></a></h1>
        </div>
        <div class="grid_12 headfoot">
            <ul class="nav main">
                <li><a href="/">Home</a>
                </li>
                <li><a href="/list">List</a>
                </li>
                <li><a href="/submitted">Submitted</a>
                </li>
                <li><a href="/faq">FAQ</a>
                </li>
                <li><a href="/api">API</a>
                </li>
                <li><a href="/raw">Raw data</a>
                </li>
                <li><a href="https://github.com/CorralPeltzer/newTrackon">Source
                    <img src="/static/imgs/GitHub.svg" alt="GitHub repo" height="30" width="30" style="vertical-align:middle;">
                    </a>
                </li>
                <li class="secondary"><a href="/about">about</a>
                </li>
            </ul>
        </div>

        ${self.body()}

        <div class="grid_12 headfoot" id="site_info">
            <div class="box center">
                <p>A <a href="https://github.com/CorralPeltzer">CorralPeltzer</a> and <a href="http://cat-v.org">cat-v.org</a> creation - <i>Because sharing is caring.</i>
                </p>
            </div>
        </div>
        <div class="clear"></div>
    </div>
</body>
</html>
<%def name="title()">newTrackon: Tracking the trackers</%def>
<%def name="extraheaders()">
</%def>
