<!DOCTYPE HTML>
<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=utf-8" />
<title>${self.title()}</title>
<link rel="stylesheet" type="text/css" href="/static/fluid960gs/all.css" media="screen">
<!--[if IE 6]><link rel="stylesheet" type="text/css" href="/static/fluid960gs/ie6.css" media="screen" /><![endif]-->
<!--[if IE 7]><link rel="stylesheet" type="text/css" href="/static/fluid960gs/ie.css" media="screen" /><![endif]-->

<link rel="stylesheet" href="/static/style.css" type="text/css">
<script type="text/javascript" src="http://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script>

</head><body>

<div class="container_12">

<div class="grid_12">
    <h1 id=branding><a href="/"><i><b>Trackon</b> <span class=small>Alpha 7</span></i></a></h1>
</div>


<div class="grid_12">
    <ul class="nav main">
        <li><a href="/">main</a></li>
        <li><a href="/api-docs">api</a></li>
        <li><a href="/incoming-log">incoming</a></li>
        <li><a href="/trackers-raw-info">raw</a></li>
        <li><a href="/faq">faq</a></li>
        <li><a href="http://repo.cat-v.org/trackon/">source</a></li>
        <li><a>links</a>
            <ul>
            <li><a href="http://repo.cat-v.org/atrack/">Atrack</a></li>
            <li><a href="http://bittrk.appspot.com/">Bittrk</a></li>
            </ul>
        </li>
        <li class=secondary><a href="/about">about</a></li>
    </ul>
</div>


${self.body()}


<div class="grid_12" id="site_info">
    <div class="box center">
        <p><a href="http://cat-v.org">A cat-v.org production</a> - <i>Because sharing is caring.</i></p>
    </div>
</div>

<div class="clear"></div>

</div>

<script type="text/javascript">
var gaJsHost = (("https:" == document.location.protocol) ? "https://ssl." : "http://www.");
document.write(unescape("%3Cscript src='" + gaJsHost + "google-analytics.com/ga.js' type='text/javascript'%3E%3C/script%3E"));
</script>
<script type="text/javascript">
try {
var pageTracker = _gat._getTracker("UA-1220719-11");
pageTracker._trackPageview();

var pageTracker2 = _gat._getTracker("UA-1220719-12");
pageTracker2._trackPageview();
} catch(err) {}</script>


</body></html>


<%def name="title()">Trackon's Lair</%def>
