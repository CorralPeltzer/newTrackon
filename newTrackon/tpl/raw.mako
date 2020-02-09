<%! from time import time %>
<%inherit file="base.mako"/>

<div class="container">
    <h2>Raw data</h2>

    <p>This is the information about the response of the last 600 trackers contacted, for research and debugging
        purposes.
        These include only trackers already in the list. </p>
    <p>The trackers are queried with a random hash.</p>

</div>

% if data:
    <div class="container-fluid">
        <div class="table-responsive">
            <table class="sortable table table-responsive table-striped table-bordered">
                <thead>
                <tr>
                    <th>Time</th>
                    <th>Tracker</th>
                    <th>IP</th>
                    <th>Result</th>
                    <th>Response/Error</th>
                </tr>
                </thead>
                % for response in data:
                    <tr>
                        <td>${response.get('time')}</td>
                        <td>${response.get('url')}</td>
                        <td>
                            % if response.get('ip'):
            ${response.get('ip')}
                            % endif
                        </td>
                        % if response.get('status') == 1:
                            <td class="up"><b>Working</b></td>
                        % else:
                            <td class="down"><b>Down</b></td>
                        % endif
                        <td>${response.get('info') | h}</td>
                    </tr>
                % endfor
            </table>
        </div>
    </div>
% endif
<%def name="title()">Raw Data - newTrackon</%def>
