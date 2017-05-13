<%! from time import time %>
<%inherit file="base.mako"/>
<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.17.1/moment.min.js"></script>
<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/livestamp/1.1.2/livestamp.min.js"></script>
<div class="container">
  <h2>Log of Newly Submitted Trackers</h2>
  <p>This is the information about the last 300 tried trackers. To make it to the queue, a tracker has to be a well-formed URL, not to be an IP, and resolve at least to an IPv4
    address.</p>
    <p>Every tracker to reach the queue is tried (in this order) with UDP, HTTPS and HTTP. When one protocol succeeds, and if its update interval is between 5 minutes and 3 hours,
      it gets added to the list. If no port is specified, the tracker is tried only with HTTPS on port 443 and HTTP on port 80.</p>
      <p>The queue is processed at about 10 seconds per URL tried.</p>
      <p><b>Number of trackers in the queue: ${size}</b></p>
    </div>
    % if data:
    <div class="container-fluid">
      <div class="table-responsive">
        <table class="sortable table table-responsive table-striped table-bordered">
          <thead>
            <tr>
              <th>Time</th>
              <th>URL</th>
              <th>IP</th>
              <th>Result</th>
              <th>Response/Error</th>
            </tr>
          </thead>
          % for response in data:
          <tr>
            <td><span data-livestamp="${response['time']}"></span></td>
            <td>${response['url']}</td>
            <td>${response.get('ip', '')}</td>
            % if response['status'] == 1:
            <td class="up"><b>Accepted</b></td>
            % else:
            <td class="rejected"><b>Rejected</b></td>
            % endif
            <td>${response['info']}</td>
          </tr>
          % endfor

          % endif
        </table>
      </div>
    </div>
    <%def name="title()">Log of submitted trackers</%def>
