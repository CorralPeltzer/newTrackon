<%inherit file="../base.mako"/>
<%def name="title()">newTrackon Frequently, Infrequently and Randomly Asked Questions</%def>
<div class="grid_12">
<h2 id="page-heading">newTrackon FAQ</h2>

<dl>
    <dt>I am trying to submit new trackers to the list but they are not added</dt>
    <dd>First, verify that the tracker is not already in the list. This includes URL and IP(s); if a tracker resolves to the same IP(s) than any tracker already in the list, that counts as duplicate.<br>
    Second, check that the tracker is currently working with your BitTorrent client, only trackers working when submitted are added to the list.<br>
    If you have checked everything and really think there is an error with newTrackon, please contact me in the 'about' section.</dd>

    <dt>I am the maintainer of a tracker and I want to change the URL in the list.</dt>
    <dd>Contact me as stated in 'about' section.</dd>

    <dt>How do I add a tracker to my torrents?</dt>
    <dd>Just go to the list section, copy the trackers and paste them in your BitTorrent client.</dd>

    <dt>How is the uptime calculated?
    <dd>Uptime is calculated based on the percentage of valid responses to the last 1000 attempts to contact the tracker. Because the interval between attempts will depend on the interval for that tracker and other factors, comparing the uptime values of different trackers is not completely 'fair'.

    <dt>Does newTrackon respect the trackers update interval?</dt>
    <dd>Yes.</dd>

    <dt>What is the picture in the about page?</dt>
    <dd>It is <i>Trago the dragon</i>, the mascot of newTrackon. It was originally
    part of "<i>The Nine Dragons</i>" handscroll (九龍圖卷) by Chen Rong (陳容), a painter of the Southern Song Dynasty during the first half of the 13th century in China. It is dated to 1244. Or anyway this is what Wikipedia claims.</dd>

    <dt>How can I help newTrackon.com?</dt>
    <dd>If you can program in Python, or know some CSS/javascript, I'm sure there are many improvements that could be made. And finally, if you find newTrackon useful, tell your friends about it, the more the merrier!
    </dd>
</dl>

</div>
