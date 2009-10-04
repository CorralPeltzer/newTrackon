<%inherit file="base.mako"/>
<div class=grid_12>
<h2 id="page-heading">Trackon FAQ</h2>

<dl>
    <dt>How is the uptime calculated?
    <dd>Uptime is calculated based on the percentage of valid responses to the last 64 attempts to contact the tracker. Because the interval between attempts will depend on the '<i>min interval</i>' for that tracker and other factors, comparing the uptime values of different trackers is not completely 'fair'.

    <dt>Why don't you support trackers that run on ports other than 80 or 443?</dt>
    <dd>Due to limitations in Google's App Engine fetchurl API it is not possible at currently to make requests to other ports.</dd>

    <dt>What is the correct pronounciation of '<i>Trackon</i>'?</dt>
    <dd>As in <i>dragon</i> but starting with <b>t</b>.</dd>

    <dt>What is the picture in the main page?</dt>
    <dd>It is part of "<i>The Nine Dragons</i>" Handscroll by Chen Rong, a painter of the Southern Song Dynastyhalf of the 13th century China. It is dated to 1244. Or anyway this is what Wikipedia claims.</dd>

</dl>

</div>

