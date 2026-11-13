def doGet(request, session):
	
    logger = system.util.getLogger("MES-REST")

    try:

        # =========================================================
        # CONFIGURATION
        # =========================================================

        EXPECTED_API_KEY = "MES123"

        # Optional:
        # Allow folder override from URL:
        #
        # https://server/api?folder=[Sample_Tags]Sine
        #
        DEFAULT_FOLDER = "[Sample_Tags]Sine"

        # =========================================================
        # REQUEST INFO
        # =========================================================

        headers = request.get('headers', {})
        params = request.get('params', {})

        clientIP = headers.get("X-Forwarded-For", "UNKNOWN")

        logger.info("Incoming MES API request from: " + str(clientIP))

        # =========================================================
        # API KEY AUTHENTICATION
        # =========================================================

        apiKey = headers.get("x-api-key")

        if apiKey is None:

            logger.warn("Missing API Key")

            return {
                "json": {
                    "status": "ERROR",
                    "message": "Missing API Key"
                },
                "status": 401
            }

        if apiKey != EXPECTED_API_KEY:

            logger.warn("Invalid API Key")

            return {
                "json": {
                    "status": "ERROR",
                    "message": "Invalid API Key"
                },
                "status": 401
            }

        # =========================================================
        # FOLDER PATH
        # =========================================================

        folderPath = params.get("folder", DEFAULT_FOLDER)

        logger.info("Reading folder: " + str(folderPath))

        # =========================================================
        # BROWSE TAGS
        # =========================================================

        try:

            browseResults = system.tag.browse(folderPath).getResults()

        except Exception as browseError:

            logger.error(
                "Tag browse failed: " + str(browseError)
            )

            return {
                "json": {
                    "status": "ERROR",
                    "message": "Failed to browse tags",
                    "details": str(browseError)
                },
                "status": 500
            }

        # =========================================================
        # VALIDATE TAGS EXIST
        # =========================================================

        if browseResults is None or len(browseResults) == 0:

            logger.warn("No tags found in folder: " + str(folderPath))

            return {
                "json": {
                    "status": "ERROR",
                    "message": "No tags found",
                    "folder": folderPath
                },
                "status": 404
            }

        # =========================================================
        # BUILD TAG PATHS
        # =========================================================

        tagPaths = []

        for tag in browseResults:

            try:

                if str(tag['tagType']) == "AtomicTag":

                    tagPaths.append(str(tag['fullPath']))

            except Exception as tagError:

                logger.warn(
                    "Skipping invalid tag: " + str(tagError)
                )

        # =========================================================
        # VALIDATE TAG PATHS
        # =========================================================

        if len(tagPaths) == 0:

            logger.warn("No AtomicTags found")

            return {
                "json": {
                    "status": "ERROR",
                    "message": "No AtomicTags found",
                    "folder": folderPath
                },
                "status": 404
            }

        # =========================================================
        # READ TAG VALUES
        # =========================================================

        try:

            values = system.tag.readBlocking(tagPaths)

        except Exception as readError:

            logger.error(
                "Tag read failed: " + str(readError)
            )

            return {
                "json": {
                    "status": "ERROR",
                    "message": "Failed to read tag values",
                    "details": str(readError)
                },
                "status": 500
            }

        # =========================================================
        # BUILD RESPONSE
        # =========================================================

        tags = []

        for i in range(len(tagPaths)):

            try:

                tagName = tagPaths[i].split("/")[-1]

                tagValue = values[i]

                tags.append({

                    "name": tagName,

                    "path": tagPaths[i],

                    "value": tagValue.value,

                    "quality": str(tagValue.quality),

                    "goodQuality": bool(tagValue.quality.isGood()),

                    "timestamp": str(tagValue.timestamp)

                })

            except Exception as valueError:

                logger.warn(
                    "Failed processing tag: " + str(valueError)
                )

        # =========================================================
        # SUCCESS RESPONSE
        # =========================================================

        response = {

            "status": "SUCCESS",

            "folder": folderPath,

            "tagCount": len(tags),

            "serverTime": str(system.date.now()),

            "tags": tags

        }

        logger.info(
            "MES API request completed successfully"
        )

        return {
            "json": response,
            "status": 200
        }

    # =============================================================
    # GLOBAL ERROR HANDLER
    # =============================================================

    except Exception as e:

        logger.error(
            "Unhandled MES API Error: " + str(e)
        )

        return {
            "json": {

                "status": "ERROR",

                "message": "Internal Server Error",

                "details": str(e)

            },
            "status": 500
        }