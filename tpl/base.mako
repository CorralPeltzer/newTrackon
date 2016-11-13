<!DOCTYPE HTML>
<html>
<head>
<meta charset="utf-8">
<title>${self.title()}</title>
<link rel="stylesheet" href="/static/fluid960gs/all.css" media="screen">
<!--[if IE 6]><link rel="stylesheet" type="text/css" href="/static/fluid960gs/ie6.css" media="screen" /><![endif]-->
<!--[if IE 7]><link rel="stylesheet" type="text/css" href="/static/fluid960gs/ie.css" media="screen" /><![endif]-->

<link rel="stylesheet" href="/static/style.css" type="text/css">
${self.extraheaders()}

</head><body>

<div class="container_12">

<div class="grid_12 headfoot">
    <h1 id=branding><a href="/"><i><b>Trackon</b></i></a></h1>
</div>


<div class="grid_12 headfoot">
    <ul class="nav main">
        <li><a href="/">main</a></li>
        <li><a href="/api-docs">api</a></li>
        <li><a href="/incoming-log">incoming</a></li>
        <li><a href="/trackers-raw-info">raw</a></li>
        <li><a href="/faq">faq</a></li>
        <li><a href="https://github.com/CorralPeltzer/newTrackon">source <img src="../static/imgs/GitHub.png" height="30px" width="30px" style="vertical-align:middle"></a></li>
        <li class=secondary><a href="/about">about</a></li>
    </ul>
</div>

<div class="grid_12 headfoot" style="text-align: right; padding-top: 1px;"><script type="text/javascript">var addthis_disable_flash = true; var addthis_pub="uriell";</script> <a href="http://www.addthis.com/bookmark.php?v=20" onmouseover="return addthis_open(this, '', '[URL]', '[TITLE]')" onmouseout="addthis_close()" onclick="return addthis_sendto()"><img src="http://s7.addthis.com/static/btn/lg-share-en.gif" width="125" height="16" alt="Bookmark and Share" style="border:0"/></a><script type="text/javascript" src="http://s7.addthis.com/js/200/addthis_widget.js"></script></div>

${self.body()}

<div class="grid_12 headfoot" id="site_info">
    <div class="box center">
        <p>A <a href="https://github.com/CorralPeltzer">CorralPeltzer</a> and <a href="http://cat-v.org">cat-v.org</a> creation - <i>Because sharing is caring.</i></p>
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


<%def name="title()">Trackon: Tracking the trackers.</%def>
<%def name="extraheaders()"></%def>
