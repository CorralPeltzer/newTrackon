<%inherit file="base.mako"/>
<%def name="title()">Trackon Frequently, Infrequently and Randomly Asked Questions</%def>
<div class=grid_12>
<h2 id="page-heading">Trackon FAQ</h2>

<dl>
    <dt>How do I add a tracker to my torrents?</dt>
    <dd>This will depend on your BitTorrent client, please consult its documentation for details. In the future we might provide instructions for the most popular BT clients, stay tunned.</dd>

    <dt>How is the uptime calculated?
    <dd>Uptime is calculated based on the percentage of valid responses to the last 64 attempts to contact the tracker. Because the interval between attempts will depend on the '<i>min interval</i>' for that tracker and other factors, comparing the uptime values of different trackers is not completely 'fair'.

    <dt>On what port numbers should trackers accept connections?</dt>
    <dd>Due to Google's limits to App Engine's fetchurl API it is only possible to make requests to ports 80-90, 440-450, and 1024-65535.</dd>

    <dt>Does Trackon respect the trackers *min interval*?</dt>
    <dd>Yes, if a tracker sets it, it will only be checked every *min interval*.</dd>

    <dt>What is the correct pronunciation of '<i>Trackon</i>'?</dt>
    <dd>As in <i>dragon</i> but starting with <b>t</b>.</dd>

    <dt>What is the picture in the about page?</dt>
    <dd>It is <i>Trago the dragon</i>, the mascot of trackon.org. It was originally
    part of "<i>The Nine Dragons</i>" handscroll (九龍圖卷) by Chen Rong (陳容), a painter of the Southern Song Dynasty during the first half of the 13th century in China. It is dated to 1244. Or anyway this is what Wikipedia claims.</dd>

    <dt>How can I help Trackon.org?</dt>
    <dd>If you can program in Python, I'm sure there are many improvements that could be made to the code ;) many new features are planned, but they will take time. If you can draw, it would be great to have a cool logo or mascot. And finally, if you find Trackon useful, tell your friends about it, the more the merrier!
    </dd>
</dl>

</div>

<%def name="title()">Trackon.org Frequently (and Infrequently) Asked Questions.</%def>
