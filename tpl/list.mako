<%inherit file="base.mako"/>
<script src="https://cdn.jsdelivr.net/clipboard.js/1.5.13/clipboard.min.js"></script>
<script>var clipboard = new Clipboard('.copy-button');</script>
<button style="margin: 30px;" class="copy-button" data-clipboard-action="copy" data-clipboard-target="#tocopy">Copy to clipboard</button>
<div id="list" style="height:62vh;width:70vh;border:1px solid #ccc;font:16px/26px Georgia, Garamond, Serif;margin: 0 0 30px 30px;overflow:auto;">
<pre id="tocopy">
${list}
</pre>
</div>