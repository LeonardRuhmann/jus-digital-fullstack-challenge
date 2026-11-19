terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# 1. Private AWS S3 Bucket for original uploaded documents
resource "aws_s3_bucket" "documents" {
  bucket = var.bucket_name

  tags = {
    Project     = "jus-digital-fullstack-challenge"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# 2. Disable Legacy ACLs (BucketOwnerEnforced - AWS recommended security standard)
resource "aws_s3_bucket_ownership_controls" "documents_ownership" {
  bucket = aws_s3_bucket.documents.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# 3. Enforce 100% Private Access (documents are served only via Presigned GET URLs)
resource "aws_s3_bucket_public_access_block" "documents_private" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 4. Default Server-Side Encryption at Rest (SSE-S3 / AES256)
resource "aws_s3_bucket_server_side_encryption_configuration" "documents_sse" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 5. Allow Front-end origin to fetch Presigned GET URLs cleanly
resource "aws_s3_bucket_cors_configuration" "documents_cors" {
  bucket = aws_s3_bucket.documents.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = [var.frontend_url]
    max_age_seconds = 3600
  }
}

# 6. Dedicated programmatic IAM User (no console login, no admin permissions)
resource "aws_iam_user" "backend_s3_user" {
  name = var.iam_user_name

  tags = {
    Project   = "jus-digital-fullstack-challenge"
    ManagedBy = "Terraform"
  }
}

# 7. Least-Privilege Policy scoped strictly to this single S3 bucket
resource "aws_iam_user_policy" "backend_s3_policy" {
  name = "JusDigitalS3BucketOnlyPolicy"
  user = aws_iam_user.backend_s3_user.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "JusDigitalBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      }
    ]
  })
}
