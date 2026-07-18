output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.url_shortener.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name of the EC2 instance"
  value       = aws_instance.url_shortener.public_dns
}
