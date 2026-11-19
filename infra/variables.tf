variable "aws_region" {
  description = "AWS region where the S3 bucket will be provisioned"
  type        = string
  default     = "sa-east-1"
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name for document storage"
  type        = string
}

variable "iam_user_name" {
  description = "Dedicated least-privilege IAM user name for the FastAPI back-end"
  type        = string
  default     = "jus-digital-backend-s3"
}

variable "frontend_url" {
  description = "Allowed origin for Presigned GET URL CORS requests"
  type        = string
  default     = "http://localhost:5173"
}

variable "environment" {
  description = "Deployment environment tag"
  type        = string
  default     = "development"
}
