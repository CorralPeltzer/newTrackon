<%inherit file="base.mako"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/clipboard.js/1.6.1/clipboard.min.js" integrity="sha256-El0fEiD3YOM7uIVZztyQzmbbPlgEj0oJVxRWziUh4UE=" crossorigin="anonymous"></script>
<script>
$('button').tooltip({
  trigger: 'click',
  placement: 'bottom'
});
function setTooltip(btn, message) {
  $(btn).tooltip('hide')
    .attr('data-original-title', message)
    .tooltip('show');
}
function hideTooltip(btn) {
  setTimeout(function() {
    $(btn).tooltip('hide');
  }, 1000);
}
var clipboard = new Clipboard('button');

clipboard.on('success', function(e) {
  setTooltip(e.trigger, 'Copied!');
  hideTooltip(e.trigger);
});

clipboard.on('error', function(e) {
  setTooltip(e.trigger, 'Failed!');
  hideTooltip(e.trigger);
});
</script>
<div class="container">
  <h2>List of stable trackers</h2>
  <p>This is a list of the <b>${size}</b> trackers with more than 95% of uptime, considered stable. You can copy the list to the clipboard and add it to your BitTorrent client.</p>
  <p><button class="btn btn-primary" data-clipboard-action="copy" data-clipboard-target="#tocopy">Copy ${size} trackers to clipboard </button><p>
    <div id="list">
      <pre id="tocopy">
${stable}
      </pre>
    </div>
  </div>
<%def name="title()">Stable Trackers - newTrackon</%def>
