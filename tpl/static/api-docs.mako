<%inherit file="../base.mako"/>
<div class=grid_12>

<h2 id="page-heading">newTrackon Web API Description</h2>

<p><b>Note: The API is still experimental and subject to change, let me know if you find it useful, or if you need any new features or changes. Thanks!</b></p>


<h3>Read API</h3>

<p>This set of APIs allows you retrive informatin about known trackers.</p>
<dl>
    <dt>GET https://newtrackon.com/api/best</dt>
    <dd>Returns a two line delimited list announce URLs of trackers that have an uptime of equal or more than 95%.</dd>

    <dt>GET https://newtrackon.com/api/:percentage</dt>
    <dd>Returns a two line delimited list announce URLs of trackers that have an uptime of equal or more than the given percentage.</dd>

    <dt>GET https://newtrackon.com/api/all</dt>
    <dd>Returns a two line delimited list announce URLs of all known trackers, dead or alive.</dd>

    <dt>GET https://newtrackon.com/api/live</dt>
    <dd>Returns a two line delimited list announce URLs of currently active and responding trackers.</dd>
</dl>

<h3>Write API</h3>
<dl>
    <dt>POST https://newtrackon.com/</dt>
    <dd>Submits a new tracker to the list that will be checked and added if alive.</dd>
</dl>
</div>

<%def name="title()">newTrackon's Web API documentation.</%def>
