def doPost(request, session):


    import system
    import base64
    import traceback

    # IMPORTANT FOR SQL VARBINARY
    from jarray import array

    logger = system.util.getLogger("POSTIMAGE")

    try:

        logger.info(
            "POST Image API Called"
        )

        # Safe payload read
        data = request.get("data", {})

        # Read fields safely
        machineId = str(
            data.get("machineId", "")
        ).strip()

        imageName = str(
            data.get("imageName", "")
        ).strip()

        imageType = str(
            data.get("imageType", "")
        ).strip()

        # Use server timestamp
        createdAt = system.date.now()

        imageBase64 = data.get(
            "imageData",
            ""
        )

        logger.info(
            "machineId=%s imageName=%s imageType=%s" %
            (
                machineId,
                imageName,
                imageType
            )
        )

        # Validate machineId
        if machineId == "":

            logger.warn(
                "machineId missing"
            )

            return {

                "json": {

                    "status":
                        "error",

                    "message":
                        "machineId missing"

                }

            }

        # Validate imageName
        if imageName == "":

            logger.warn(
                "imageName missing"
            )

            return {

                "json": {

                    "status":
                        "error",

                    "message":
                        "imageName missing"

                }

            }

        # Validate imageData
        if imageBase64 == "":

            logger.warn(
                "imageData missing"
            )

            return {

                "json": {

                    "status":
                        "error",

                    "message":
                        "imageData missing"

                }

            }

        # Decode Base64 safely
        try:

            logger.info(
                "Decoding Base64 image"
            )

            decoded = base64.b64decode(
                imageBase64
            )

            # CRITICAL:
            # Convert to Java byte[]
            imageBytes = array(
                decoded,
                'b'
            )

        except Exception as decodeError:

            logger.error(
                "Base64 decode failed"
            )

            logger.error(
                str(decodeError)
            )

            return {

                "json": {

                    "status":
                        "error",

                    "message":
                        "Invalid Base64 image"

                }

            }

        # Log image size ONLY
        logger.info(
            "Image Size Bytes = %s" %
            len(imageBytes)
        )

        # SQL Insert Query
        query = """
        INSERT INTO Images
        (
            machineId,
            imageName,
            imageData,
            imageType,
            createdAt
        )
        VALUES
        (
            ?, ?, ?, ?, ?
        )
        """

        logger.info(
            "Executing SQL Insert"
        )

        # Execute Insert
        rows = system.db.runPrepUpdate(
            query,
            [
                machineId,
                imageName,
                imageBytes,
                imageType,
                createdAt
            ],
            "Dev_MSSQL_Server"
        )

        logger.info(
            "Image inserted successfully"
        )

        # Success Response
        return {

            "json": {

                "status":
                    "success",

                "rowsAffected":
                    rows,

                "machineId":
                    machineId,

                "imageName":
                    imageName,

                "imageType":
                    imageType,

                "createdAt":
                    str(createdAt)

            }

        }

    except Exception as e:

        # IMPORTANT:
        # NEVER LOG FULL imageBase64
        # NEVER LOG imageBytes

        logger.error(
            "POST Image Error: " +
            str(e)
        )

        logger.error(
            traceback.format_exc()
        )

        return {

            "json": {

                "status":
                    "error",

                "message":
                    str(e)

            }

        }