import React from "react";
import { styles, Text, Button, Icon, Layout, Input } from "../components/import";


const Login: React.FC = () => {

	const handleClick = () => {
    alert('Button clicked!');
  };

	return (
		<div className={styles.loginBackground}>
			<Layout direction="column" align="center" gap={32}>
				<Layout direction="row"align="center" gap={16}>
					<Icon name="logo-tepsys"/>
					<Text content="CNレポート" size="lg" weight="bold"/>
				</Layout>
				<Input
					supportText="ログインID"
					placeholder="LoginID"
					onChange={(e) => console.log("ログインID:", e.target.value)}
				/>
				<Input
					supportText="パスワード"
					placeholder="Password"
					onChange={(e) => console.log("パスワード:", e.target.value)}
				/>
				<Button text="Login" variant="primary" onClick={handleClick}/>
			</Layout>
		</div>
	);
};

export default Login;