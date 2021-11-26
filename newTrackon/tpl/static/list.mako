<%inherit file="../base.mako"/>
<script>

    var selectedList = 'api/stable?include_ipv4_only_trackers=1&include_ipv6_only_trackers=0'

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
        setTimeout(function () {
            $(btn).tooltip('hide');
        }, 1000);
    }

    function getTrackers(api_url) {
        $.get({
            url: api_url,
            data: null,
            success: function (text) {
                $('#tocopy').text(text);
                size = (text.match(/^\s*\S/gm) || "").length;
                $('#size').text(size);
            },
            dataType: 'text'
        });
    }

    $(document).ready(function () {
        getTrackers(selectedList);
        $('#include_ipv6_only').change(function () {
            if (this.checked) {
                selectedList = selectedList.replace('include_ipv6_only_trackers=0','include_ipv6_only_trackers=1');
                getTrackers(selectedList);
            } else {
                selectedList = selectedList.replace('include_ipv6_only_trackers=1','include_ipv6_only_trackers=0');
                getTrackers(selectedList);
            }
        });
        $('#include_ipv4_only').change(function () {
            if (this.checked) {
                selectedList = selectedList.replace('include_ipv4_only_trackers=0','include_ipv4_only_trackers=1');
                getTrackers(selectedList);
            } else {
                selectedList = selectedList.replace('include_ipv4_only_trackers=1','include_ipv4_only_trackers=0');
                getTrackers(selectedList);
            }
        });
    });

    var clipboard = new ClipboardJS('.btn');

    clipboard.on('success', function (e) {
        setTooltip(e.trigger, 'Copied!');
        hideTooltip(e.trigger);
    });

    clipboard.on('error', function (e) {
        setTooltip(e.trigger, 'Failed!');
        hideTooltip(e.trigger);
    });
</script>
<div class="container">
    <h2>List of stable trackers</h2>
    <p>This is a list of trackers with more than 95% of uptime, considered stable. You can copy the
        list and add it to your torrents or directly to your BitTorrent client.</p>
    <div class="row">
        <div class="col-lg-3">
            <p>
                <button class="btn btn-primary" data-clipboard-action="copy" data-clipboard-target="#tocopy">Copy <b
                        id="size"></b>
                    trackers to clipboard
                </button>
            </p>
        </div>
        <div class="col-lg-3">
            <p>
                <label class="btn btn-default"><input type="checkbox" id="include_ipv4_only" checked> Include IPv4-only trackers</label>
            </p>
        </div>
        <div class="col-lg-3">
            <p>
                <label class="btn btn-default"><input type="checkbox" id="include_ipv6_only"> Include IPv6-only trackers</label>
            </p>
        </div>
    </div>
    <div id="list">
        <pre id="tocopy">Loading...</pre>
    </div>
</div>
<%def name="title()">Stable Trackers List - newTrackon</%def>
