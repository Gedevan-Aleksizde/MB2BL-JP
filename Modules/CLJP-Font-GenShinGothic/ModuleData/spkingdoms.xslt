<?xml version='1.0' encoding='UTF-8'?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:output omit-xml-declaration="yes"/>
  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>
  <xsl:template match="Kingdom[@id='aserai']/@name"><xsl:attribute name="name">{=aserainamemissing}Aserai</xsl:attribute></xsl:template>
  <xsl:template match="Kingdom[@id='battania']/@name"><xsl:attribute name="name">{=xkewCbr1lW}Battania</xsl:attribute></xsl:template>
  <xsl:template match="Kingdom[@id='khuzait']/@name"><xsl:attribute name="name">{=WdDohR60ER}Khuzait</xsl:attribute></xsl:template>
  <xsl:template match="Kingdom[@id='sturgia']/@name"><xsl:attribute name="name">{=XfrwOymPAf}Sturgia</xsl:attribute></xsl:template>
  <xsl:template match="Kingdom[@id='vlandia']/@name"><xsl:attribute name="name">{=LcBnSFcZkD}Vlandia</xsl:attribute></xsl:template>
</xsl:stylesheet>