def doGet(request, session):


    import system
    import base64
    import traceback

    logger = system.util.getLogger("GETIMAGE")

    try:

        logger.info(
            "GET Image API Called"
        )

        # Get request params safely
        params = request.get("params", {})

        machineId = str(
            params.get("machineId", "")
        ).strip()

        logger.info(
            "machineId = %s" %
            machineId
        )

        # Validate input
        if machineId == "":

            logger.warn(
                "machineId missing"
            )

            return {

                "json": {

                    "status": "error",

                    "message":
                        "machineId parameter required"

                }

            }

        # SQL Query
        query = """
        SELECT TOP 1
            machineId,
            imageName,
            imageType,
            createdAt,
            imageData
        FROM Images
        WHERE machineId = ?
        ORDER BY createdAt DESC
        """

        logger.info(
            "Executing SQL Query"
        )

        # Execute query
        rows = system.db.runPrepQuery(
            query,
            [machineId],
            "Dev_MSSQL_Server"
        )

        logger.info(
            "Rows fetched = %s" %
            str(len(rows))
        )

        # No data found
        if len(rows) == 0:

            logger.warn(
                "No image found for machineId = %s" %
                machineId
            )

            return {

                "json": {

                    "status": "not_found",

                    "machineId":
                        machineId,

                    "message":
                        "No image found"

                }

            }

        # Get first row
        row = rows[0]

        logger.info(
            "Encoding image to Base64"
        )

        # Convert image blob safely
        imageBase64 = ""

        if row["imageData"] is not None:
        	 imageBytes=bytes(bytearray(row["imageData"]))
        	 imageBase64 = base64.b64encode(imageBytes).decode("utf-8")

        # Build response
        response = {

            "status": "success",

            "machineId":
                str(row["machineId"]),

            "imageName":
                str(row["imageName"]),

            "imageType":
                str(row["imageType"]),

            "createdAt":
                str(row["createdAt"]),

            "imageData":
                imageBase64

        }

        logger.info(
            "Returning API response"
        )

        # IMPORTANT FOR WEBDEV
        return {

            "json": response
            

        }

    except Exception as e:

        logger.error(
            traceback.format_exc()
        )

        return {

            "json": {

                "status": "error",

                "message":
                    str(e)

            }

        }