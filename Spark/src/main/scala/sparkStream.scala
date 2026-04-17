// src/main/scala/sparkDay2/ContractRiskAssessment.scala
package main.scala

import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.spark.SparkConf
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import org.apache.spark.streaming._
import org.apache.spark.streaming.kafka010._
import org.apache.log4j.{Level, Logger}

object sparkStream {
  val logger = Logger.getLogger(getClass.getName)

  // MySQL 配置
  val dbConfig = Map(
    "url" -> "jdbc:mysql://localhost:3306/contract_db?useSSL=false",
    "user" -> "root",
    "password" -> "123456",
    "driver" -> "com.mysql.cj.jdbc.Driver"
  )

  def main(args: Array[String]): Unit = {
    // 设置日志级别
    Logger.getLogger("org.apache.spark").setLevel(Level.WARN)
    Logger.getLogger("org.apache.kafka").setLevel(Level.WARN)

    // Spark 配置
    val conf = new SparkConf().setAppName("ContractRiskAssessment").setMaster("local[*]")
    val ssc = new StreamingContext(conf, Seconds(5))

    // 初始化 SparkSession
    val spark = SparkSession.builder
      .config(conf)
      .getOrCreate()

    import spark.implicits._

    // Kafka 消费者配置
    val kafkaParams = Map[String, Object](
      "bootstrap.servers" -> "127.0.0.1:9092",
      "key.deserializer" -> classOf[StringDeserializer],
      "value.deserializer" -> classOf[StringDeserializer],
      "group.id" -> "niit",
      "auto.offset.reset" -> "latest",
      "enable.auto.commit" -> (false: java.lang.Boolean)
    )

    val topics = Array("contract_risk_assessment")

    // 创建 Kafka 直接数据流
    val stream = KafkaUtils.createDirectStream[String, String](
      ssc,
      LocationStrategies.PreferConsistent,
      ConsumerStrategies.Subscribe[String, String](topics, kafkaParams)
    )

    // 定义数据结构
    val schema = new StructType()
      .add("contract_name", StringType)
      .add("contract_type", StringType)
      .add("contract_amount", DoubleType)
      .add("payment_terms", StringType)
      .add("performance_period_start", StringType)
      .add("performance_period_end", StringType)
      .add("deliverables", StringType)
      .add("breach_clauses", StringType)
      .add("dispute_resolution", StringType)
      .add("party_a_credit_rating", StringType)
      .add("party_b_credit_rating", StringType)
      .add("market_conditions", StringType)
      .add("industry_trends", StringType)
      .add("customer_id", StringType)

    // 处理 Kafka 流数据
    stream.foreachRDD { rdd =>
      if (!rdd.isEmpty()) {
        // 将 RDD[ConsumerRecord[String, String]] 转换为 DataFrame
        val df = rdd.map(record => record.value).toDF("value")
          .select(from_json(col("value"), schema).alias("data"))
          .select("data.*")

        // 计算风险指数
        val riskDF = calculateRiskIndex(df)

        // 输出到控制台
        riskDF.show()

        // 将结果写入 MySQL
        try {
          riskDF.write
            .format("jdbc")
            .option("url", dbConfig("url"))
            .option("dbtable", "contract_risk_results")
            .option("user", dbConfig("user"))
            .option("password", dbConfig("password"))
            .option("driver", dbConfig("driver"))
            .option("batchsize", "1000")
            .mode("append")
            .save()
        } catch {
          case e: Exception =>
            logger.error("写入 MySQL 失败", e)
        }
      }
    }

    // 启动流处理
    ssc.start()
    ssc.awaitTermination()
  }

  def calculateRiskIndex(df: DataFrame): DataFrame = {
    // 定义风险计算逻辑
    val weights = Map(
      "amount_score" -> 0.2,
      "payment_score" -> 0.1,
      "performance_score" -> 0.1,
      "deliverables_score" -> 0.1,
      "breach_score" -> 0.1,
      "dispute_score" -> 0.1,
      "party_a_score" -> 0.1,
      "party_b_score" -> 0.1,
      "market_score" -> 0.05,
      "industry_score" -> 0.05
    )

    val riskIndex = weights.foldLeft(lit(0.0)) { case (acc, (colName, weight)) =>
      acc + col(colName) * weight
    }

    df.withColumn("amount_score", when(col("contract_amount") > 1000000, 5.0)
        .when(col("contract_amount") > 500000, 4.0)
        .when(col("contract_amount") > 100000, 3.0)
        .when(col("contract_amount") > 50000, 2.0)
        .otherwise(1.0))
      .withColumn("payment_score", when(col("payment_terms").contains("预付款"), 2.0)
        .when(col("payment_terms").contains("分期付款"), 3.0)
        .otherwise(4.0))
      .withColumn("datediff", datediff(to_date(col("performance_period_end")), to_date(col("performance_period_start"))).cast("double"))
      .withColumn("performance_score",
        when(col("datediff") > 365, 5.0)
          .when(col("datediff") > 180, 4.0)
          .when(col("datediff") > 90, 3.0)
          .when(col("datediff") > 30, 2.0)
          .otherwise(1.0))
      .withColumn("deliverables_score", when(col("deliverables").contains("复杂"), 5.0)
        .when(col("deliverables").contains("中等"), 3.0)
        .otherwise(2.0))
      .withColumn("breach_score", when(col("breach_clauses").contains("高额违约金"), 5.0)
        .when(col("breach_clauses").contains("中等违约金"), 3.0)
        .otherwise(2.0))
      .withColumn("dispute_score", when(col("dispute_resolution").contains("仲裁"), 3.0)
        .when(col("dispute_resolution").contains("诉讼"), 4.0)
        .otherwise(5.0))
      .withColumn("party_a_score", when(col("party_a_credit_rating") === "AAA", 1.0)
        .when(col("party_a_credit_rating") === "AA", 2.0)
        .when(col("party_a_credit_rating") === "A", 3.0)
        .when(col("party_a_credit_rating") === "B", 4.0)
        .otherwise(5.0))
      .withColumn("party_b_score", when(col("party_b_credit_rating") === "AAA", 1.0)
        .when(col("party_b_credit_rating") === "AA", 2.0)
        .when(col("party_b_credit_rating") === "A", 3.0)
        .when(col("party_b_credit_rating") === "B", 4.0)
        .otherwise(5.0))
      .withColumn("market_score", when(col("market_conditions").contains("不稳定"), 5.0)
        .when(col("market_conditions").contains("波动"), 4.0)
        .otherwise(3.0))
      .withColumn("industry_score", when(col("industry_trends").contains("下降"), 5.0)
        .when(col("industry_trends").contains("平稳"), 3.0)
        .otherwise(2.0))
      .withColumn("risk_index", riskIndex)
      .withColumn("risk_level", when(col("risk_index") <= 3.2, "低风险")
        .when(col("risk_index") <= 3.6, "中风险")
        .otherwise("高风险"))
      .select(
        "contract_name",
        "contract_type",
        "contract_amount",
        "payment_terms",
        "performance_period_start",
        "performance_period_end",
        "deliverables",
        "breach_clauses",
        "dispute_resolution",
        "party_a_credit_rating",
        "party_b_credit_rating",
        "market_conditions",
        "industry_trends",
        "customer_id",
        "risk_index",
        "risk_level"
      )
  }
}