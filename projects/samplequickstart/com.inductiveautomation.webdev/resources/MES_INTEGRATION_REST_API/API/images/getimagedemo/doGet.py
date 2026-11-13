def doGet(request, session):
	import time
	import base64
	import traceback
	
	logger = system.util.getLogger("GETIMAGE")
	
	try:
	    TOTAL_IMAGES = 10
	    logger.info("GET Image API Called")
	
	    current_minute = int(time.time() / 60)
	    ImageId = (current_minute % TOTAL_IMAGES) +1
	
	    # Two machine locations
	    #normal_loc = "ACOT10" + str(ImageId)
	    #cal_loc    = "ACAL10" + str(ImageId)
	    normal_loc = "THR1{:02d}".format(ImageId)
	    cal_loc    = "EDG1{:02d}".format(ImageId)
	    logger.info("Dynamic machine locations = %s, %s" % (normal_loc, cal_loc))
	
	    query = """
	        SELECT TOP 1
	            machinelocation,
	            status,
	            pinholes,
	            imageName,
	            imageData,
	            imageType,
	            createdAt,
	            uploadedAt
	        FROM images_demo
	        WHERE imageType = ?
	        ORDER BY createdAt DESC
	    """
	
	    # --- First machine (normal) ---
	    rows = system.db.runPrepQuery(query, [normal_loc], "Dev_MSSQL_Server")
	    if len(rows) > 0:
	        row = rows[0]
	        imageBase64 = ""
	        if row["imageData"] is not None:
	            imageBytes = bytes(bytearray(row["imageData"]))
	            imageBase64 = base64.b64encode(imageBytes).decode("utf-8")
	
	        normal_response = {
	            "status": str(row["status"]),
	            "machinelocation": str(row["machinelocation"]),
	            "pinholes": str(row["pinholes"]),
	            "imageName": str(row["imageName"]),
	            "defectcode": str(row["imageType"]),
	            "createdAt": str(row["createdAt"]),
	            "imageData": imageBase64
	        }
	    else:
	        normal_response = {
	            "status": "not_found",
	            "machinelocation": normal_loc,
	            "message": "No image found"
	        }
	
	    # --- Second machine (cal) ---
	    rows = system.db.runPrepQuery(query, [cal_loc], "Dev_MSSQL_Server")
	    if len(rows) > 0:
	        row = rows[0]
	        imageBase64 = ""
	        if row["imageData"] is not None:
	            imageBytes = bytes(bytearray(row["imageData"]))
	            imageBase64 = base64.b64encode(imageBytes).decode("utf-8")
	
	        cal_response = {
	            "calStatus": str(row["status"]),
	            "calMachinelocation": str(row["machinelocation"]),
	            "calPinholes": str(row["pinholes"]),
	            "calImageName": str(row["imageName"]),
	            "calDefectCode": str(row["imageType"]),
	            "calcreatedAt": str(row["createdAt"]),
	            "calImageData": imageBase64
	        }
	    else:
	        cal_response = {
	            "calStatus": "not_found",
	            "calMachinelocation": cal_loc,
	            "calMessage": "No image found"
	        }
	
	    # Merge in fixed order
	    response = {}
	    response.update(normal_response)
	    response.update(cal_response)
	
	    logger.info("Returning combined API response")
	    return {"json": response}
	
	except Exception as e:
	    logger.error(traceback.format_exc())
	    return {
	        "json": {
	            "status": "error",
	            "message": str(e)
	        }
	    }