# ============================================================
# METADATA CACHE
# Purpose:
# Load TagMaster metadata from SQL and provide fast lookup
# using the OPC UA NodeId.
# ============================================================

_metadataCache = {}


# ============================================================
# 1. LOAD METADATA FROM SQL
# ============================================================

def getAllMetadata():

    query = """
        SELECT
            TagID,
            SourceTag,
            OPCUA_NodeId,
            Enterprise,
            Site,
            Area,
            Segment,
            Unit,
            FBS_Mod1,
            FBS_Mod1_Name,
            FBS_Mod2,
            FBS_Mod2_Name,
            FBS_Device,
            FBS_Device_Name,
            DataSource,
            DataSourceName,
            Enabled
        FROM dbo.TagMaster
        WHERE Enabled = 1
    """

    return system.db.runPrepQuery(
        query,
        [],
        "Dev_MSSQL_Server"
    )


# ============================================================
# 2. REFRESH IN-MEMORY METADATA CACHE
# ============================================================

def refreshCache():

    global _metadataCache

    data = getAllMetadata()

    cache = {}

    for row in data:

        nodeId = row["OPCUA_NodeId"]

        if nodeId:
            cache[nodeId] = row

    _metadataCache = cache

    return len(_metadataCache)


# ============================================================
# 3. GET METADATA USING OPC UA NODE ID
# ============================================================

def getMetadata(nodeId):

    return _metadataCache.get(nodeId)


# ============================================================
# 4. GET TAG CONTEXT
# Purpose:
# Combine live Ignition tag value with SQL metadata.
# ============================================================

def getTagContext(tagPath, nodeId):

    # Read live value from Ignition
    qv = system.tag.readBlocking([tagPath])[0]

    # Get metadata from cache
    metadata = getMetadata(nodeId)

    if metadata is None:
        return None

    return {
        "TagPath": tagPath,
        "OPCUA_NodeId": nodeId,
        "Value": qv.value,
        "Quality": str(qv.quality),

        "SourceTag": metadata["SourceTag"],

        "Enterprise": metadata["Enterprise"],
        "Site": metadata["Site"],
        "Area": metadata["Area"],
        "Segment": metadata["Segment"],
        "Unit": metadata["Unit"],

        "FBS_Mod1": metadata["FBS_Mod1"],
        "FBS_Mod1_Name": metadata["FBS_Mod1_Name"],

        "FBS_Mod2": metadata["FBS_Mod2"],
        "FBS_Mod2_Name": metadata["FBS_Mod2_Name"],

        "FBS_Device": metadata["FBS_Device"],
        "FBS_Device_Name": metadata["FBS_Device_Name"],

        "DataSource": metadata["DataSource"],
        "DataSourceName": metadata["DataSourceName"]
    }


# ============================================================
# 5. BUILD CONTEXTUAL PATH
# Example:
# AGRATAS/IN11/E155/PAE/NTC11/UWD001/COR001/TAC001/Tag
# ============================================================

def buildContextPath(metadata):

    parts = [
        metadata["Enterprise"],
        metadata["Site"],
        metadata["Area"],
        metadata["Segment"],
        metadata["Unit"],
        metadata["FBS_Mod1"],
        metadata["FBS_Mod2"],
        metadata["FBS_Device"],
        metadata["SourceTag"]
    ]

    return "/".join(
        [str(x) for x in parts if x is not None and str(x) != ""]
    )


# ============================================================
# 6. BUILD FINAL CONTEXTUALIZED PAYLOAD
# Purpose:
# Combine live value, quality, timestamp, OPC UA identity,
# and contextual metadata into one payload.
# ============================================================

def buildPayload(tagPath, nodeId):

    metadata = getMetadata(nodeId)

    if metadata is None:
        return None

    # Read live value from Ignition
    qv = system.tag.readBlocking([tagPath])[0]

    # Generate contextual path
    contextPath = buildContextPath(metadata)

    return {
        "ContextPath": contextPath,
        "TagPath": tagPath,
        "OPCUA_NodeId": nodeId,

        "Value": qv.value,
        "Quality": str(qv.quality),
        "Timestamp": qv.timestamp,

        "SourceTag": metadata["SourceTag"],

        "Enterprise": metadata["Enterprise"],
        "Site": metadata["Site"],
        "Area": metadata["Area"],
        "Segment": metadata["Segment"],
        "Unit": metadata["Unit"],

        "FBS_Mod1": metadata["FBS_Mod1"],
        "FBS_Mod1_Name": metadata["FBS_Mod1_Name"],

        "FBS_Mod2": metadata["FBS_Mod2"],
        "FBS_Mod2_Name": metadata["FBS_Mod2_Name"],

        "FBS_Device": metadata["FBS_Device"],
        "FBS_Device_Name": metadata["FBS_Device_Name"],

        "DataSource": metadata["DataSource"],
        "DataSourceName": metadata["DataSourceName"]
    }