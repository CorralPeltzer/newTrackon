<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="utf-8">
    <title>${self.title()}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#087F23">
    <meta name="author" content="Miguel Angel Corral Peltzer">
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
    <link rel="icon" type="image/png" href="/favicon-32x32.png" sizes="32x32">
    <link rel="icon" type="image/png" href="/favicon-16x16.png" sizes="16x16">
    <link rel="manifest" href="/manifest.json">
    <link rel="mask-icon" href="/safari-pinned-tab.svg" color="#25802c">
    <link rel="stylesheet" href="/static/css/theme.css"/>
    <link rel="stylesheet" href="/static/css/custom.css"/>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto"/>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.9.0/css/all.min.css"
          integrity="sha256-UzFD2WYH2U1dQpKDjjZK72VtPeWP50NoJjd26rnAdUI=" crossorigin="anonymous"/>

    % if active == 'main':
        <link rel="stylesheet" href="https://cdn.datatables.net/v/bs/dt-1.10.15/r-2.1.1/datatables.min.css"/>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/flag-icon-css/3.3.0/css/flag-icon.min.css"
              integrity="sha256-NkXMfPcpoih3/xWDcrJcAX78pHpfwxkhNj0bAf8AMTs=" crossorigin="anonymous"/>
    % endif
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.4.1/jquery.min.js"
            integrity="sha256-CSXorXvZcTkaix6Yvo6HppcZGetbYMGWSFlBw8HfCJo=" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/3.4.1/js/bootstrap.min.js"
            integrity="sha256-nuL8/2cJ5NDSSwnKD8VqreErSWHtnEP9E7AySL+1ev4=" crossorigin="anonymous"></script>
    % if active == 'main':
        <script src="https://cdn.datatables.net/v/bs/dt-1.10.15/r-2.1.1/datatables.min.js"></script>
        <script src="https://cdn.datatables.net/plug-ins/1.10.15/sorting/natural.js"></script>
        <script src="https://cdn.datatables.net/plug-ins/1.10.15/sorting/date-eu.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.24.0/moment.min.js"
                integrity="sha256-4iQZ6BVL4qNKlQ27TExEhBN1HFPvAvAMbFavKKosSWQ=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/livestamp/1.1.2/livestamp.min.js"
                integrity="sha256-8r65KJgULBDiZhwDydfWrEkx3yyV/grGsGzaekobngI=" crossorigin="anonymous"></script>
    % endif
    % if active == 'list':
        <script src="https://cdnjs.cloudflare.com/ajax/libs/clipboard.js/2.0.4/clipboard.min.js"
                integrity="sha256-FiZwavyI2V6+EXO1U+xzLG3IKldpiTFf3153ea9zikQ=" crossorigin="anonymous"></script>
    % endif
    % if active == 'submitted':
        <script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.24.0/moment.min.js"
                integrity="sha256-4iQZ6BVL4qNKlQ27TExEhBN1HFPvAvAMbFavKKosSWQ=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/livestamp/1.1.2/livestamp.min.js"
                integrity="sha256-8r65KJgULBDiZhwDydfWrEkx3yyV/grGsGzaekobngI=" crossorigin="anonymous"></script>
    % endif
</head>

<body>
<div class="navbar navbar-default navbar-fixed-top">
    <div class="container">
        <div class="navbar-header">
            <a href="" class="navbar-brand">newTrackon</a>
            <button class="navbar-toggle" type="button" data-toggle="collapse" data-target="#navbar-main">
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
            </button>
        </div>
        <div class="navbar-collapse collapse" id="navbar-main">
            <ul class="nav navbar-nav">
                % if active == 'main':
                    <li class="active"><a href="/"><i class="fas fa-home" aria-hidden="true"></i> Home</a></li>
                % else:
                    <li><a href="/"><i class="fas fa-home" aria-hidden="true"></i> Home</a></li>
                % endif
                % if active == 'list':
                    <li class="active"><a href="/list"><i class="fas fa-list" aria-hidden="true"></i> List</a></li>
                % else:
                    <li><a href="/list"><i class="fas fa-list" aria-hidden="true"></i> List</a></li>
                % endif
                % if active == 'submitted':
                    <li class="active"><a href="/submitted"><i class="fas fa-plus" aria-hidden="true"></i> Submitted</a>
                    </li>
                % else:
                    <li><a href="/submitted"><i class="fas fa-plus" aria-hidden="true"></i> Submitted</a></li>
                % endif
                % if active == 'faq':
                    <li class="active"><a href="/faq"><i class="fas fa-question-circle" aria-hidden="true"></i> FAQ</a>
                    </li>
                % else:
                    <li><a href="/faq"><i class="fas fa-question-circle" aria-hidden="true"></i> FAQ</a></li>
                % endif
                % if active == 'api':
                    <li class="active"><a href="/api"><i class="fas fa-code" aria-hidden="true"></i> API</a></li>
                % else:
                    <li><a href="/api"><i class="fas fa-code" aria-hidden="true"></i> API</a></li>
                % endif
                % if active == 'raw':
                    <li class="active"><a href="/raw"><i class="fas fa-terminal" aria-hidden="true"></i> Raw data</a>
                    </li>
                % else:
                    <li><a href="/raw"><i class="fas fa-terminal" aria-hidden="true"></i> Raw data</a></li>
                % endif
                <li><a href="https://github.com/CorralPeltzer/newTrackon"><i class="fab fa-github"
                                                                             aria-hidden="true"></i> Source</a></li>
            </ul>
            <ul class="nav navbar-nav navbar-right">
                % if active == 'about':
                    <li class="active"><a href="/about"><i class="fas fa-user" aria-hidden="true"></i> About</a></li>
                % else:
                    <li><a href="/about"><i class="fas fa-user" aria-hidden="true"></i> About</a></li>
                % endif
            </ul>
        </div>
    </div>
</div>

    ${self.body()}

<footer class="footer">
    <p class="text-center">A <a href="https://twitter.com/CorralPeltzer">@CorralPeltzer</a> creation based on an <a
            href="http://uriel.cat-v.org/">Uriel</a> project</p>
</footer>
</body>
</html>
