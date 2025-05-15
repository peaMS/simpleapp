<!DOCTYPE html>
<?php
// Depending on platform get hostname (either from OS or from IMDS)
if ($platform == "vm") {
    $cmd = "curl -s --connect-timeout 1 -H Metadata:true http://169.254.169.254/metadata/instance?api-version=2017-08-01";
    $metadataJson = shell_exec($cmd);
    # If no IMDS access fall back to the OS name
    if (!(empty($metadataJson))) {
        $metadata = json_decode($metadataJson, true);
        $hostname = $metadata['compute']['name'];
    } else {
        $hostname = shell_exec('hostname');
    }
} else {
    $hostname = shell_exec('hostname');
}
?>
<html lang="en">
    <head>
        <title><?php print($page_title); ?></title>
        <meta charset="utf-8">
        <meta http-equiv="X-UA-Compatible" content="IE-edge">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="Description" lang="en" content="Azure VM Info Page">
        <meta name="robots" content="index, follow">
        <!-- icons -->
        <link rel="apple-touch-icon" href="apple-touch-icon.png">
        <link rel="shortcut icon" href="favicon.ico">
        <!-- CSS file -->
        <link rel="stylesheet" href="styles.css">
    </head>
    <body>
        <div class="nav-bar">
            <div class="container">
                <ul class="nav">
                <li><a href="index.php">Home</a></li>
                <li><a href="healthcheck.html">Healthcheck</a></li>
                <li><a href="healthcheck.php">PHPinfo</a></li>
                </ul>
            </div>
        </div>
        <div class="content" <?php print((empty(getenv("BACKGROUND"))) ? "" : "style=\"background-color:" . getenv("BACKGROUND") . ";\"");?> >
            <div class="container">
                <div class="main">
                    <h1>Container <?php print($hostname); ?></h1>
                    <h3>IP log</h3>
                    <p>This section contains information resulting of calling some endpoints of the API. This will only work if the environment variable API_URL is set to the correct instance of an instance of the API:</p>
                    <p><b>API_URL</b>: <?php print(getenv("API_URL")); ?></p>
                    <?php
                        $cmd = "curl " . getenv("API_URL") . "/api/healthcheck";
                        $result_json = shell_exec($cmd);
                        $result = json_decode($result_json, true);
                        $sql_output = $result["health"];
                        print("<p><b>API health check</b>: " . $sql_output . "</p>");
                    ?>
                    <?php
                        $cmd = "curl --connect-timeout 3 " . getenv("API_URL") . "/api/sqlversion";
                        $result_json = shell_exec($cmd);
                        $result = json_decode($result_json, true);
                        $sql_output = $result["sql_output"][0]["VERSION()"];
                    ?>
                    <p><b>MySQL version</b>: <?php print($sql_output); ?></p>
                    <p><b>Logs:</b></p>
                    <?php
                        $cmd = "curl --connect-timeout 3 " . getenv("API_URL") . "/api/srcipget";
                        $result_json = shell_exec($cmd);
                        $result = json_decode($result_json, true);
                        $logs = $result["srciplog"]["sql_output"];
                        if (count($logs)) {
                            // Open the table
                            print("<table border=\"1\">");
                            print('<tr><th>IP address</th><th>Timestamp</th></tr>');
                            // Cycle through the array
                            foreach ($logs as $log) {
                                // Output a row
                                print("<tr>");
                                print("<td>" . $log["ip"] . "</td>");
                                print("<td>" . $log["timestamp"] . "</td>");
                                print("</tr>");
                            }
                            // Close the table
                            print("</table>");
                        } else {
                            print("<p>No logs found</p>");
                        }
                    ?>
                    <br>
                    <h3>Add new log entry</h3>
                    <p>Press this button to add your IP address (<?php print($_SERVER['REMOTE_ADDR'])?>) to the log:</p>
                    <form action="index.php#srciplog" method="get">
                        <input type="hidden" id="command" name="command" value="srciplog">
                        <input type="submit">
                    </form>
                    <?php 
                        if (strcmp($_GET["command"], 'srciplog') == 0) {
                            $cmd = "curl --connect-timeout 3 " . getenv("API_URL") . "/api/srciplog?ip=" . $_SERVER['REMOTE_ADDR'];
                            $result_json = shell_exec($cmd);
                            $result = json_decode($result_json, true);
                            print("<p>IP address added: <b>" . $_SERVER['REMOTE_ADDR'] . "</b></p>");
                        }
                    ?>
                    <br>
                    <h3>Initialize database</h3>
                    <p>Press this button to delete all existing records from the log:</p>
                    <form action="index.php#srcipinit" method="get">
                        <input type="hidden" id="command" name="command" value="srcipinit">
                        <input type="submit">
                    </form>
                    <?php 
                        if (strcmp($_GET["command"], 'srcipinit') == 0) {
                            $cmd = "curl --connect-timeout 3 " . getenv("API_URL") . "/api/srcipinit";
                            $result_json = shell_exec($cmd);
                            $result = json_decode($result_json, true);
                            print("<p>Database initialized successfully</p>");
                        }
                    ?>
                </div>
            </div>
        </div>
        <div class="footer">
            <div class="container">
                MIT License
            </div>
        </div>
    </body>
</html>
