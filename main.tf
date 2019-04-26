data "aws_partition" "current" {}
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}


resource "aws_iam_role" "lambda" {
  name = "${var.prefix}_windows_password_rotation"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "ssmfull" {
  #name       = "${var.prefix}_ssm_full"
  role      = "${aws_iam_role.lambda.name}"
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMFullAccess"
}

resource "aws_iam_role_policy_attachment" "lambdabasic" {
  #name       = "${var.prefix}_lambda_basic"
  role      = "${aws_iam_role.lambda.name}"
  policy_arn ="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


data "aws_iam_policy_document" "secretmanager" {
  statement {
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue",
      "secretsmanager:PutSecretValue",
      "secretsmanager:UpdateSecretVersionStage",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:*",
    ]
  }
  statement {
    actions = ["secretsmanager:GetRandomPassword"]
    resources = ["*",]
  }
}

resource "aws_iam_policy" "secretmanager" {
  name   = "${var.prefix}_secretmanager"
  path   = "/"
  policy = "${data.aws_iam_policy_document.secretmanager.json}"
}

resource "aws_iam_role_policy_attachment" "secretmanager" {
  #name       = "${var.prefix}_secretmanager"
  role      = "${aws_iam_role.lambda.name}"
  policy_arn = "${aws_iam_policy.secretmanager.arn}"
}

variable "filename" { default = "windows_rotation"}
resource "aws_lambda_function" "lambda" {
  filename           = "${path.module}/${var.filename}.zip"
  function_name      = "${var.prefix}-${var.filename}"
  role               = "${aws_iam_role.lambda.arn}"
  handler            = "${var.filename}.lambda_handler"
  source_code_hash   = "${base64sha256(file("${path.module}/${var.filename}.zip"))}"
  runtime            = "python2.7"
  timeout            = 90
  description        = "this function works only called by secret manager and using ssm can rotate password in windows"
  environment {
    variables = { #https://docs.aws.amazon.com/general/latest/gr/rande.html#asm_region
      SECRETS_MANAGER_ENDPOINT = "https://secretsmanager.${data.aws_region.current.name}.amazonaws.com"
      KMS_KEY_ID = "${data.aws_kms_key.ssm.id}"
    }
  }
}

data "aws_kms_key" "ssm" {
  key_id = "alias/aws/ssm"
}

resource "aws_lambda_permission" "allow_secret_manager_call_Lambda" {
    function_name = "${aws_lambda_function.lambda.function_name}"
    statement_id = "AllowExecutionSecretManager"
    action = "lambda:InvokeFunction"
    principal = "secretsmanager.amazonaws.com"
}
