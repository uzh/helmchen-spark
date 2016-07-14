def initSpark(nbBackend):
    import os
    if nbBackend == 'openstack':
        os.environ['SPARK_HOME'] = "/usr/local/spark"

    # setup Spark
    import findspark # SPARK_HOME needs to be set for import of findspark
    findspark.init()
    import pyspark
    from pyspark import SparkContext, SparkConf

    conf = SparkConf()

    if nbBackend == 'local':
        # options for Spark on local machine
        master = 'local'
    elif nbBackend == 'openstack':
        # options for Spark on OpenStack cluster
        master = 'spark://sparkcluster-controller001:7077'
    else:
        print "Backend " + nbBackend + " not known"

    conf.setMaster(master)
    # configure the max. number of cores a user may request
    conf.set("spark.cores.max", 4)

    try:
        sc = SparkContext(conf=conf)
        return sc
    except ValueError as exception:
        print "Could not create SparkContext. Maybe it exists already?"
