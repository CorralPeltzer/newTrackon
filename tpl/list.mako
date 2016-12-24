<%inherit file="base.mako"/>
<script src="https://cdn.jsdelivr.net/clipboard.js/1.5.13/clipboard.min.js"></script>
<script>var clipboard = new Clipboard('.copy-button');</script>
<div class="grid_12">
<h2 id="page-heading">List of stable trackers</h2>
<p>This is a list of all trackers with more than 95% of uptime, considered stable. You can copy the list to the clipboard and add it to your BitTorrent client.</p>
<p><button class="copy-button" data-clipboard-action="copy" data-clipboard-target="#tocopy">Copy to clipboard </button><p>
<div id="list"
     style="height:62vh;width:70vh;border:1px solid #ccc;font:16px/26px Georgia, Garamond, Serif;overflow:auto;">
<pre id="tocopy">
${list}
</pre>
</div>
</div>