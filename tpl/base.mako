<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>${self.title()}</title>
    <link rel="stylesheet" href="/static/fluid960gs/all.css" media="screen">
    <link rel='shortcut icon' type='image/x-icon' href='/static/imgs/favicon.ico' />
    <!--[if IE 6]><link rel="stylesheet" type="text/css" href="/static/fluid960gs/ie6.css" media="screen" /><![endif]-->
    <!--[if IE 6]><link rel="stylesheet" type="text/css" href="/static/fluid960gs/ie6.css" media="screen" /><![endif]-->
    <!--[if IE 7]><link rel="stylesheet" type="text/css" href="/static/fluid960gs/ie.css" media="screen" /><![endif]-->
    <link rel="stylesheet" href="/static/style.css" type="text/css"> ${self.extraheaders()}
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