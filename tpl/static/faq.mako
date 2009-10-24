<%inherit file="base.mako"/>
<%def name="title()">Trackon Frequently, Infrequently and Randomly Asked Questions</%def>
<div class=grid_12>
<h2 id="page-heading">Trackon FAQ</h2>

<dl>
    <dt>How is the uptime calculated?
    <dd>Uptime is calculated based on the percentage of valid responses to the last 64 attempts to contact the tracker. Because the interval between attempts will depend on the '<i>min interval</i>' for that tracker and other factors, comparing the uptime values of different trackers is not completely 'fair'.

    <dt>On what port numbers should trackers accept connections?</dt>
    <dd>Due to Google's limits to App Engine's fetchurl API it is only officially possible to make requests to ports 80 and 443. In practice it seems to be possible to contact trackers listening on any of the following ports: 80, 443, 4443, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8188, 8444, 8990. (Thanks to Medecau for alerting me to this list found in the pubsubhubbub source.) If you would like trackers on other ports to be accessible please star <a href="http://code.google.com/p/googleappengine/issues/detail?id=418">issue 418</a> on the official App Engine issue tracker.</dd>

    <dt>What is the correct pronounciation of '<i>Trackon</i>'?</dt>
    <dd>As in <i>dragon</i> but starting with <b>t</b>.</dd>

    <dt>What is the picture in the main page?</dt>
    <dd>It is <i>Trago the dragon</i>, the mascot of tracko.org. It was originally
    part of "<i>The Nine Dragons</i>" handscroll (九龍圖卷) by Chen Rong (陳容), a painter of the Southern Song Dynasty during the first half of the 13th century in China. It is dated to 1244. Or anyway this is what Wikipedia claims.</dd>

</dl>

</div>

<%def name="title()">Trackon.org Frequently (and Infrequently) Asked Questions.</%def>
