<%inherit file="base.mako"/>
<script src="https://cdn.jsdelivr.net/clipboard.js/1.5.13/clipboard.min.js"></script>
<script>var clipboard = new Clipboard('.copy-button');</script>
<div class="container">
  <h2>List of stable trackers</h2>
  <p>This is a list of the <b>${size}</b> trackers with more than 95% of uptime, considered stable. You can copy the list to the clipboard and add it to your BitTorrent client.</p>
  <p><button class="copy-button btn btn-default" data-clipboard-action="copy" data-clipboard-target="#tocopy">Copy ${size} trackers to clipboard </button><p>
    <div id="list">
      <pre id="tocopy">
${stable}
      </pre>
    </div>
  </div>
