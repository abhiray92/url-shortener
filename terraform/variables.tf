variable "key_pair_name" {
  description = "EC2 key pair name"
  type        = string
  default     = "url-shortener-key"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}
