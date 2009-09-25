<%inherit file="base.mako"/>
<div class=grid_12>

<h2 id="page-heading">Trackon Web API</h2>

<p>Trackon has a minimalist and RESTful API, divided in two main parts:</p>

<h3>Read API</h3>

<p>This set of APIs allows you retrive informatin about known trackers.</p>
<dl>
    <dt>GET /api/live</dt>
    <dd>Returns a new-line delimited list announce URLs of currenlty active and responding trackers.</dd>

    <dt>GET /api/trackers</dt>
    <dd>Returns a JSON object with all the information associated with all known trackers, the specific infomration included is still subject to change.</dd>
</dl>

<h3>Write API</h3>

<p>Still not decided what set of write APIs will be provided, probably at least some way to submit new trackers programatically, and to request an update of the tracker status and metadata.</p>

<h2 class="page-heading">Terms of Shirvice</h2>

<p>Do whatever the hell you want as long as you don't try to DoS me, and if you power some website or app by using this APIs it would be cool if you link to trackon.</p>

</div>
