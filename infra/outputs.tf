output "s3_bucket_name" {
  description = "Provisioned private S3 bucket name"
  value       = aws_s3_bucket.documents.bucket
}

output "s3_bucket_arn" {
  description = "Provisioned S3 bucket ARN"
  value       = aws_s3_bucket.documents.arn
}

output "iam_user_name" {
  description = "Dedicated IAM user for FastAPI S3 access"
  value       = aws_iam_user.backend_s3_user.name
}
