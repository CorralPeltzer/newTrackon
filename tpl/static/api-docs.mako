<%inherit file="../base.mako"/>
<div class="container">
  <h2>HTTP API documentation</h2>
  <h3>Read API</h3>
  <p>This set of APIs allows you retrive informatin about known trackers.</p>
  <dl>
    <dt>GET <a href="/api/stable">https://newtrackon.com/api/stable</a></dt>
    <dd>Returns a two line delimited list announce URLs of trackers that have an uptime of equal or more than 95%.</dd>

    <dt>GET <a href="/api/70">https://newtrackon.com/api/:percentage</a></dt>
    <dd>Returns a two line delimited list announce URLs of trackers that have an uptime of equal or more than the given percentage.</dd>

    <dt>GET <a href="/api/all">https://newtrackon.com/api/all</a></dt>
    <dd>Returns a two line delimited list announce URLs of all known trackers, dead or alive.</dd>

    <dt>GET <a href="/api/live">https://newtrackon.com/api/live</a></dt>
    <dd>Returns a two line delimited list announce URLs of currently active and responding trackers.</dd>

    <dt>GET <a href="/api/udp">https://newtrackon.com/api/udp</a></dt>
    <dd>Returns a two line delimited list announce URLs of stable and UDP trackers.</dd>

    <dt>GET <a href="/api/http">https://newtrackon.com/api/http</a></dt>
    <dd>Returns a two line delimited list announce URLs of stable and HTTP/HTTPS trackers.</dd>
  </dl>
  <h3>Write API</h3>
  <dl>
    <dt>POST https://newtrackon.com/api/add</dt>
    <dd>Submits new trackers to the list that will be checked and added if alive.</dd>
    <dd>Body: "application/x-www-form-urlencoded" Content Type, with an URL encoded body with the only key as "new_trackers" and its value the trackers separated by any whitespace character.</dd>
    <dd>Response: 204 HTTP empty response.</dd>
    </dl>
  </div>
  <%def name="title()">API - newTrackon</%def>
