# Terraform AWS Windows Password Lambda Rotation
When you create an EC2 windows the password will remain the same for the whole life of the machine. It can be rotated automatically with this module

This module is a dependencie of https://registry.terraform.io/modules/giuseppeborgese/windows-password-rotation-secret-manager/

Full guide on https://medium.com/@giuseppeborgese/aws-windows-password-rotation-with-custom-secret-manager-92f95f44aa40

## Prerequisites

* The ec2 machine is already created and needs to have a role with a policy ssm arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM
* The SSM needs to work on the machines if it is not the password is not replaced and the old one with pem key remains, nothing brokes.
* To change a password it is not necessary to know the previous password because SSM runs as a daemon.

## Infrastructure and steps
Using the terraform modules it will be created

* One lambda function for account and region
* For each machine a secret manager record, all the records call the same functions.

### Creations steps:
Create one lambda function for each region you are working on. Using this code

``` hcl
module "windows-password-lambda-rotation" {
  source  = "giuseppeborgese/windows-password-lambda-rotation/aws"
  prefix  = "pep"
}
```
* Before applying the rotation try to run a simple command like this to the machine, to see if ssm commands can run, check the output in the run command history

``` hcl
aws ssm send-command --instance-ids i-xxxxxxxxx --document-name AWS-RunPowerShellScript --parameters commands="dir c:"
``` 

* For each EC2 Windows machine create a new secret manager record and connected to the function using this code

``` hcl
module "windows-password-rotation-secret-manager2019" {
  source  = "giuseppeborgese/windows-password-rotation-secret-manager/aws"
  secret_name_prefix = "vault_"
  instanceid = "i-xxxxxx"
  rotation_lambda_arn = "${module.windows-password-lambda-rotation.lambda_arn}"
}
``` 
* You can rotate the password manually using the rotation button or wait the numbers of days defined
* You can still recover the old password from the web console but it will NOT work

** Youtube video
I did a full creation and configuration in this video

[![AWS Windows password rotation with Custom Secret Manager](https://img.youtube.com/vi/BU0Gy814crQ/0.jpg)](https://youtu.be/BU0Gy814crQ)

so you can see all the details and don’t miss anything. There is also a troubleshooting phase.

# Rotation steps what happens behind the scene:
This image describes all the steps every time there is a rotation manual or automatic

![schema](https://raw.githubusercontent.com/giuseppeborgese/terraform-aws-windows-password-rotation-secret-manager/master/schema.png)

Let's read in details:

1. The secret manager record triggers a lambda function passing its parameters.
2. The Lambda extract the instance id from the called record and generates a new password with the predefined criteria
3. The lambda stores the new password in the original Secret Manager record using the default key aws/secretsmanager
4. The Lambda stores encrypted the password in the system manager parameter store using the default key aws/ssm
5. The lambda runs a call to SSM run command this runs a PowerShell command in the EC2 machine.
6. The EC2 machine recovers the password from parameter store by Powershell
7. The lambda deletes the password from the parameter store.

You cannot pass the password as a parameter in the shell script because it will be shown in cleartext the System Manager log, it has to “travel” between services always encrypted.

# Feedback
if you like this module leave a comment or a thumbs up in the youtube video or in the medium article. 
