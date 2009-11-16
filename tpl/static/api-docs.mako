<%inherit file="base.mako"/>
<div class=grid_12>

<h2 id="page-heading">Trackon Web API Description</h2>

<p><b>Note: The API is still experimental and subject to change, let us know if you find it useful, or if you need any new features or changes. Thanks!</b></p>

<p>Trackon has a minimalist and RESTful API, divided in two main parts:</p>

<h3>Read API</h3>

<p>This set of APIs allows you retrive informatin about known trackers.</p>
<dl>
    <dt>GET /api/live</dt>
    <dd>Returns a new-line delimited list announce URLs of currenlty active and
    responding trackers.</dd>

    <dt>GET /api/fail</dt>
    <dd>Returns a new-line delimited list announce URLs of trackers that failed their last check.</dd>

    <dt>GET /api/all</dt>
    <dd>Returns a new-line delimited list announce URLs of all known trackers, dead or alive.</dd>

    <dt>GET /api/trackers.json (Not yet implemented!)</dt>
    <dd>Returns a JSON object with all the information associated with all
    known trackers, the specific infomration included is still subject to
    change.</dd> </dl>

<h3>Write API</h3>

<p>Still not decided what set of write APIs will be provided, probably at least
some way to submit new trackers programatically, and to request an update of
the tracker status and metadata.</p>

<hr>
<h3>Terms of Shirvice(sic)</h3>

<p>Do whatever the hell you want as long as you don't try to DoS me, and if you
power some website or app by using this APIs it would be cool if you link to
trackon.</p>


<h3>License</h3>

<p>All the information and data provided through this API is in the <i>Public Domain</i> and
you are free to do whatever perverted things you like with it, just don't
complain to me if something breaks ;) (But bug reports are of course very welcome.)</p>

<p><i>Note: I hate legalese, and this notice is only here to make chelz happy ;P</i></p>

</div>

<%def name="title()">Trackon's Web API documentation.</%def>
